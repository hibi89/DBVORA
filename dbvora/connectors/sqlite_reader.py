"""Restricted SQLite metadata-only connector.

Only a user-supplied absolute local path is accepted. Every connection is opened
with SQLite mode=ro; arbitrary SQL is not accepted by this interface.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import stat

from dbvora.errors import InventoryError

SQLITE_MAGIC = b"SQLite format 3\x00"
MAX_DB_BYTES = 16 * 1024 ** 4  # inventory cap (16 TiB), not content extraction


def validate_path(user_path: str | Path) -> tuple[Path, int, int]:
    """Return canonical file path, byte size and mtime ns; never echo input on error."""
    if not isinstance(user_path, (str, Path)) or not str(user_path):
        raise InventoryError("INVALID_PATH", "Provide an absolute SQLite file path.")
    path = Path(user_path).expanduser()
    if not path.is_absolute():
        raise InventoryError("INVALID_PATH", "Provide an absolute SQLite file path.")
    # Reject links throughout the path, not only its final component.
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise InventoryError("SYMLINK_FORBIDDEN", "Symbolic-link paths are not supported.")
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise InventoryError("INVALID_FILE", "A regular SQLite file is required.")
        if info.st_size > MAX_DB_BYTES:
            raise InventoryError("TOO_LARGE", "The SQLite file exceeds the inventory size limit.")
        with path.open("rb") as source:
            magic = source.read(len(SQLITE_MAGIC))
        if magic != SQLITE_MAGIC or info.st_size < 100:
            raise InventoryError("INVALID_FILE", "The selected file is not a SQLite database.")
    except OSError:
        raise InventoryError("FILE_UNAVAILABLE", "Cannot read the selected SQLite file.") from None
    return path.resolve(strict=True), info.st_size, info.st_mtime_ns


@contextmanager
def read_only_connection(path: Path):
    """Open existing SQLite in mode=ro and expose metadata-only operations upstream."""
    try:
        con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.25)
    except sqlite3.Error:
        raise InventoryError("DB_OPEN_FAILED", "Cannot open the SQLite database read-only.") from None
    try:
        con.execute("PRAGMA query_only=ON")
        con.execute("PRAGMA trusted_schema=OFF")
        con.execute("PRAGMA busy_timeout=250")
        yield con
    finally:
        con.close()
