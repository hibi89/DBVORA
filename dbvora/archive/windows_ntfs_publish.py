"""Experimental NTFS create-only publication, synthetic temporary files ONLY.

Not integrated with DBVORA's archive release path; a successful result is not
proof of directory-metadata durability or survival of physical power failure.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

MOVEFILE_WRITE_THROUGH = 0x00000008
_SYNTHETIC_ROOT = re.compile(r"^dbvora-win32-synthetic-[A-Za-z0-9_-]+$")
_STAGED_NAME = re.compile(r"^\.dbvora-stage-[0-9a-f]{32}\.part$")
_TARGET_NAME = re.compile(r"^dbvora-[0-9a-f]{32}\.bin$")


class WinPublishError(Exception):
    """Stable reason without paths, OS exception strings or file bytes."""


def _windows_volume_type(directory: Path) -> str:
    """Query the actual output drive, not just the default TEMP drive."""
    if os.name != "nt":
        return "NOT_WINDOWS"
    try:
        root = Path(directory).anchor
        if not root:
            return "UNAVAILABLE"
        name = ctypes.create_unicode_buffer(40)
        fn = ctypes.WinDLL("kernel32", use_last_error=True).GetVolumeInformationW
        fn.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                       ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                       ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
        fn.restype = wintypes.BOOL
        return name.value.upper() if fn(root, None, 0, None, None, None, name, len(name)) else "UNAVAILABLE"
    except (OSError, TypeError, ValueError, AttributeError):
        return "UNAVAILABLE"


def _windows_temp_filesystem() -> str:
    if os.name != "nt":
        return "NOT_WINDOWS"
    try:
        root = Path(tempfile.gettempdir()).anchor
        if not root:
            return "UNAVAILABLE"
        name = ctypes.create_unicode_buffer(40)
        fn = ctypes.WinDLL("kernel32", use_last_error=True).GetVolumeInformationW
        fn.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                       ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                       ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
        fn.restype = wintypes.BOOL
        return name.value.upper() if fn(root, None, 0, None, None, None, name, len(name)) else "UNAVAILABLE"
    except (OSError, TypeError, ValueError, AttributeError):
        return "UNAVAILABLE"


def _native_move_write_through(stage: Path, target: Path) -> None:
    """No REPLACE_EXISTING, COPY_ALLOWED or DELAY_UNTIL_REBOOT flags."""
    if os.name != "nt":
        raise WinPublishError("WINDOWS_REQUIRED")
    try:
        fn = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
        fn.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
        fn.restype = wintypes.BOOL
        ok = fn(str(stage), str(target), MOVEFILE_WRITE_THROUGH)
    except (OSError, AttributeError, TypeError, ValueError):
        raise WinPublishError("MOVE_API_UNAVAILABLE") from None
    if not ok:
        raise WinPublishError("MOVE_FAILED")


def _is_windows_reparse_point(path: Path) -> bool:
    """Refuse a reparse-point fixture root, including Windows junctions."""
    if os.name != "nt":
        return False
    try:
        get_attrs = ctypes.WinDLL("kernel32", use_last_error=True).GetFileAttributesW
        get_attrs.argtypes = (wintypes.LPCWSTR,)
        get_attrs.restype = wintypes.DWORD
        attrs = get_attrs(str(path))
        return attrs == 0xFFFFFFFF or bool(attrs & 0x400)
    except (OSError, TypeError, ValueError, AttributeError):
        return True


def _validate_synthetic_paths(root: Path, staged: Path, target: Path) -> None:
    try:
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
        if (not isinstance(root, Path) or not isinstance(staged, Path) or not isinstance(target, Path)
                or not _SYNTHETIC_ROOT.fullmatch(root.name)
                # Windows may spell TEMP using an 8.3 alias (RUNNER~1).
                # Compare canonical *locations*, while rejecting reparse roots
                # and symbolic-link path components to prevent an escape.
                or root.parent.resolve(strict=True) != temp_root
                or root.resolve(strict=True).parent != temp_root
                or any(part.is_symlink() for part in (root, *root.parents))
                or _is_windows_reparse_point(root)
                or staged.parent != root or target.parent != root
                or not _STAGED_NAME.fullmatch(staged.name)
                or not _TARGET_NAME.fullmatch(target.name)):
            raise WinPublishError("UNSAFE_SYNTHETIC_PATH")
    except (OSError, RuntimeError):
        raise WinPublishError("UNSAFE_SYNTHETIC_PATH") from None


def _file_digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(64 * 1024), b""):
            sha.update(data)
    return sha.hexdigest()


def _commit_synthetic_staged(root: Path, staged: Path, target: Path, *, move=None) -> str:
    """Commit generated temporary fixture only. move is a test-only seam."""
    _validate_synthetic_paths(root, staged, target)
    if os.path.lexists(target):
        raise WinPublishError("DESTINATION_EXISTS")
    try:
        before = staged.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or staged.is_symlink():
            raise WinPublishError("UNSAFE_STAGE")
        # Windows FlushFileBuffers requires a writable file handle.
        with staged.open("r+b") as inp:
            opened = os.fstat(inp.fileno())
            if ((opened.st_dev, opened.st_ino, opened.st_size) !=
                (before.st_dev, before.st_ino, before.st_size)):
                raise WinPublishError("STAGE_CHANGED")
            os.fsync(inp.fileno())
        expected = _file_digest(staged)
        mover = _native_move_write_through if move is None else move
        mover(staged, target)
        if not target.is_file() or target.is_symlink() or staged.exists():
            raise WinPublishError("PUBLISH_STATE_INVALID")
        if target.stat().st_size != before.st_size or _file_digest(target) != expected:
            raise WinPublishError("PUBLISHED_BYTES_DIFFER")
        return expected
    except WinPublishError:
        raise
    except OSError:
        raise WinPublishError("STAGE_OR_PUBLISH_IO_FAILED") from None
