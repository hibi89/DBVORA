"""Fail-closed cleanup limited to a uniquely generated DBVORA HTML report."""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

_OUTPUT_NAME = re.compile(r"dbvora-workspace-[0-9a-f]{32}\.html\Z")


def remove_new_report(directory: str | Path, filename: str, created_stat: os.stat_result | None) -> bool:
    """Remove only the exact regular inode created by this operation.

    On any uncertainty (missing inode, replacement, symlink, filesystem error),
    retain the candidate instead of risking deletion of a user-owned file.
    """
    if (created_stat is None or type(filename) is not str
            or _OUTPUT_NAME.fullmatch(filename) is None
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
