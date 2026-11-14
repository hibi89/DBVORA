"""Local resource measurements with explicit provenance; never DB-server CPU/RAM."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time

CONTRACT = "dbvora.local-process-resources.v1"
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


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ResourceError("INVALID_ARGUMENT")


def main(argv=None):
    parser = _SafeParser(description="Explicit local process/volume sample only")
    parser.add_argument("--local-dir", required=True)
    try:
        args = parser.parse_args(argv)
        print(json.dumps({"ok": True, "report": observe(args.local_dir)}, sort_keys=True))
        return 0
    except ResourceError as exc:
        error = str(exc)
    except Exception:
        error = "RESOURCE_OBSERVATION_FAILED"
    print(json.dumps({"ok": False, "error_code": error}, sort_keys=True), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
