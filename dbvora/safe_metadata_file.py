"""Bounded read-only JSON from explicitly chosen, existing local regular files.

No symlink paths, FIFOs, network, arbitrary file URLs or SQL. The opened file
handle is validated and read with a fixed byte ceiling, not an unchecked
read_text() after an earlier path.stat(). Concurrently hostile directory swaps
remain outside this local single-user MVP's security certification.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat


class MetadataInputError(Exception):
    """Fixed public code; never contain local paths or JSON values."""


def _object_without_duplicates(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON property")
        result[key] = value
    return result


def _reject_constant(_value: str):
    raise ValueError("Non-standard JSON constant")


def read_local_json(raw: str | Path, *, max_bytes: int):
    """Parse at most max_bytes from a regular file; reject JSON ambiguity.

    Path checks are defensive, not a guarantee against privileged concurrent
    processes changing parent directories. O_NOFOLLOW is used when supported.
    """
    if (not isinstance(raw, (Path, str)) or not isinstance(max_bytes, int)
            or isinstance(max_bytes, bool) or not 2 <= max_bytes <= 1024 * 1024):
        raise MetadataInputError("INVALID_METADATA_FILE")
    path = Path(raw)
    if not path.is_absolute():
        raise MetadataInputError("INVALID_METADATA_FILE")
    try:
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise MetadataInputError("INVALID_METADATA_FILE")
        # Inspect before opening to reject FIFOs/devices before an open could
        # block on them. Recheck via fstat after open, and bound the read too.
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or not 2 <= before.st_size <= max_bytes:
            raise MetadataInputError("INVALID_METADATA_FILE")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if (not stat.S_ISREG(opened.st_mode) or not 2 <= opened.st_size <= max_bytes
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
                raise MetadataInputError("INVALID_METADATA_FILE")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(max_bytes + 1)
            if not 2 <= len(data) <= max_bytes or len(data) != opened.st_size:
                raise MetadataInputError("INVALID_METADATA_FILE")
        finally:
            os.close(fd)
        return json.loads(data.decode("utf-8"), object_pairs_hook=_object_without_duplicates,
                          parse_constant=_reject_constant)
    except (OSError, UnicodeError, ValueError, RecursionError, TypeError):
        raise MetadataInputError("INVALID_METADATA_FILE") from None
