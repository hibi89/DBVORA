"""Fail-closed cleanup limited to uniquely generated DBVORA report artifacts."""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

_NAMES = {
    "report": re.compile(r"dbvora-workspace-[0-9a-f]{32}\.html\Z"),
    "observation": re.compile(r"dbvora-observation-[0-9a-f]{32}\.json\Z"),
}


def _remove_created(directory: str | Path, filename: str,
                    created_stat: os.stat_result | None, kind: str) -> bool:
    """Delete only a generated regular file still matching its opening inode.

    If identity cannot be confirmed, retain the file; this is a best-effort
    same-directory cleanup, not a power-loss or hostile-race guarantee.
    """
    pattern = _NAMES.get(kind)
    if (created_stat is None or type(filename) is not str or pattern is None
            or pattern.fullmatch(filename) is None
            or not stat.S_ISREG(created_stat.st_mode)
            or not created_stat.st_ino):
        return False
    target = Path(directory) / filename
    try:
        current = target.lstat()
        if (not stat.S_ISREG(current.st_mode)
                or current.st_dev != created_stat.st_dev
                or current.st_ino != created_stat.st_ino):
            return False
        target.unlink()
        return True
    except OSError:
        return False


def remove_new_report(directory: str | Path, filename: str,
                      created_stat: os.stat_result | None) -> bool:
    return _remove_created(directory, filename, created_stat, "report")


def remove_new_observation(directory: str | Path, filename: str,
                           created_stat: os.stat_result | None) -> bool:
    return _remove_created(directory, filename, created_stat, "observation")
