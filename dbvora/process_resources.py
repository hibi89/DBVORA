"""Local resource measurements with explicit provenance; never DB-server CPU/RAM."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import time

CONTRACT = "dbvora.local-process-resources.v1"
TREND_CONTRACT = "dbvora.local-process-trend.v1"
_MAX_COUNTER = 2**63 - 1
_INSTANCE_ID = secrets.token_hex(16)  # Process-local; not a persistent device identifier.
_ID = re.compile(r"[a-f0-9]{32}\Z")
class ResourceError(ValueError):
    """Fixed code, without private paths."""


def _directory(raw):
    if not isinstance(raw, (Path, str)) or not Path(raw).is_absolute():
        raise ResourceError("INVALID_LOCAL_DIRECTORY")
    p = Path(raw)
    try:
        for item in (p, *p.parents):
            if stat.S_ISLNK(item.lstat().st_mode):
                raise ResourceError("SYMLINK_LOCAL_DIRECTORY")
        if not stat.S_ISDIR(p.lstat().st_mode):
            raise ResourceError("INVALID_LOCAL_DIRECTORY")
    except ResourceError:
        raise
    except OSError:
        raise ResourceError("INVALID_LOCAL_DIRECTORY") from None
    return p


def _ram():
    """Resident bytes for this interpreter only; do not invent missing data."""
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/self/statm", "rt", encoding="ascii") as stream:
                values = stream.read(128).split()
            pages = int(values[1])
            size = pages * int(os.sysconf("SC_PAGE_SIZE"))
            if 0 < size <= 2**63 - 1:
                return size, "linux_proc_self_statm_resident_bytes"
        except (OSError, ValueError, IndexError, OverflowError):
            pass
    elif sys.platform == "win32":
        try:
            import ctypes
            class PM(ctypes.Structure):
                _fields_ = [("cb", ctypes.c_uint32), ("PageFaultCount", ctypes.c_uint32),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            data = PM()
            data.cb = ctypes.sizeof(data)
            kernel = ctypes.windll.kernel32
            kernel.GetCurrentProcess.restype = ctypes.c_void_p
            psapi = ctypes.windll.psapi.GetProcessMemoryInfo
            psapi.argtypes = (ctypes.c_void_p, ctypes.POINTER(PM), ctypes.c_uint32)
            psapi.restype = ctypes.c_int
            if psapi(kernel.GetCurrentProcess(), ctypes.byref(data), ctypes.sizeof(data)) == 1:
                size = int(data.WorkingSetSize)
                if 0 < size <= 2**63 - 1:
                    return size, "windows_psapi_getprocessmemoryinfo_working_set"
        except (AttributeError, OSError, ValueError, TypeError):
            pass
    return None, "unavailable"


def observe(local_dir):
    local = _directory(local_dir)
    clock = time.monotonic_ns()
    cpu = time.process_time_ns()
    ram, source = _ram()
    try:
        disk = shutil.disk_usage(local)
        if not (0 <= disk.free <= disk.total <= 2**63 - 1):
            raise OSError("counter out of range")
        volume = {"status": "measured", "total_bytes": int(disk.total),
                  "free_bytes": int(disk.free),
                  "source": "shutil_disk_usage_explicit_local_volume",
                  "scope": "containing_volume_not_database_file_or_server"}
    except OSError:
        volume = {"status": "unavailable",
                  "scope": "containing_volume_not_database_file_or_server"}
    return {
        "contract": CONTRACT, "status": "observed_local_process_not_db_server",
        "process_id": os.getpid(), "process_instance_id": _INSTANCE_ID,
        "process_cpu_time_ns": cpu,
        "process_cpu_scope": "cumulative_current_python_process_cpu_not_cpu_percent",
        "sample_monotonic_ns": clock,
        "ram": {"status": "measured" if ram is not None else "unavailable",
                "resident_bytes": ram, "source": source,
                "scope": "current_python_process_not_database_server"},
        "disk": volume, "database_server_cpu_percent": None,
        "database_server_ram_bytes": None, "automatic_actions": False,
        "ready_for_customer_data": False,
    }



def _valid_comparable_sample(sample):
    """Reject unscoped or legacy observations instead of fabricating CPU trends."""
    if type(sample) is not dict or sample.get("contract") != CONTRACT:
        return False
    if sample.get("status") != "observed_local_process_not_db_server":
        return False
    if (type(sample.get("process_id")) is not int or
            not 0 < sample["process_id"] <= _MAX_COUNTER or
            type(sample.get("process_instance_id")) is not str or
            not _ID.fullmatch(sample["process_instance_id"])):
        return False
    if sample.get("process_cpu_scope") != "cumulative_current_python_process_cpu_not_cpu_percent":
        return False
    if (sample.get("database_server_cpu_percent") is not None or
            sample.get("database_server_ram_bytes") is not None):
        return False
    for name in ("sample_monotonic_ns", "process_cpu_time_ns"):
        value = sample.get(name)
        if type(value) is not int or not 0 <= value <= _MAX_COUNTER:
            return False
    ram = sample.get("ram")
    if type(ram) is not dict or ram.get("scope") != "current_python_process_not_database_server":
        return False
    if ram.get("status") == "measured":
        if (type(ram.get("resident_bytes")) is not int or
                not 0 < ram["resident_bytes"] <= _MAX_COUNTER or
                ram.get("source") not in (
                    "linux_proc_self_statm_resident_bytes",
                    "windows_psapi_getprocessmemoryinfo_working_set")):
            return False
    elif ram.get("status") == "unavailable":
        if ram.get("resident_bytes") is not None or ram.get("source") != "unavailable":
            return False
    else:
        return False
    return True


def compare_local_samples(previous, current):
    """Compare two observations from ONE Python process, not a DB or host.

    The caller owns sampling cadence. No file, network, scheduler or metadata
    persistence is involved; no OS-wide or database-server CPU % is derived.
    """
    base = {
        "contract": TREND_CONTRACT,
        "scope": "same_python_process_only_not_database_server",
        "database_server_cpu_percent": None,
        "database_server_ram_bytes": None,
        "automatic_actions": False,
        "ready_for_customer_data": False,
    }
    def unavailable(reason):
        return {**base, "status": "unavailable", "reason": reason,
                "elapsed_ns": None, "process_cpu_delta_ns": None,
                "resident_ram_delta_bytes": None}
    if not _valid_comparable_sample(previous) or not _valid_comparable_sample(current):
        return unavailable("invalid_or_legacy_observation")
    if (previous["process_id"] != current["process_id"] or
            previous["process_instance_id"] != current["process_instance_id"]):
        return unavailable("different_python_process")
    elapsed = current["sample_monotonic_ns"] - previous["sample_monotonic_ns"]
    if elapsed <= 0:
        return unavailable("non_increasing_monotonic_clock")
    cpu_delta = current["process_cpu_time_ns"] - previous["process_cpu_time_ns"]
    if cpu_delta < 0:
        return unavailable("process_cpu_counter_decreased")
    before_ram, after_ram = previous["ram"], current["ram"]
    ram_comparable = (before_ram["status"] == after_ram["status"] == "measured"
                      and before_ram["source"] == after_ram["source"])
    return {
        **base, "status": "measured_two_samples_only_no_forecast",
        "elapsed_ns": elapsed, "process_cpu_delta_ns": cpu_delta,
        "cpu_delta_scope": "process_cpu_time_not_cpu_utilization_percent",
        "resident_ram_status": "measured" if ram_comparable else "unavailable",
        "resident_ram_delta_bytes": (
            after_ram["resident_bytes"] - before_ram["resident_bytes"]
            if ram_comparable else None),
        "resident_ram_scope": "same_process_resident_memory_not_database_server",
    }


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ResourceError("INVALID_ARGUMENT")


def main(argv=None):
    parser = _SafeParser(description="Explicit local process/volume sample only")
    parser.add_argument("--local-dir", required=True)
    parser.add_argument("--sample-interval-ms", type=int,
                        help="Optional two measurements in one process (100-5000 ms)")
    try:
        args = parser.parse_args(argv)
        interval = args.sample_interval_ms
        if interval is not None and not 100 <= interval <= 5000:
            raise ResourceError("INVALID_SAMPLE_INTERVAL")
        if interval is None:
            report = observe(args.local_dir)
        else:
            first = observe(args.local_dir)
            time.sleep(interval / 1000)
            latest = observe(args.local_dir)
            report = {"contract": "dbvora.local-process-trend-cli.v1",
                      "latest_sample": latest,
                      "comparison": compare_local_samples(first, latest)}
        print(json.dumps({"ok": True, "report": report}, sort_keys=True))
        return 0
    except ResourceError as exc:
        error = str(exc)
    except Exception:
        error = "RESOURCE_OBSERVATION_FAILED"
    print(json.dumps({"ok": False, "error_code": error}, sort_keys=True), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
