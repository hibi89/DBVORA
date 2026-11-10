"""Match SQLite's ASCII-only identifier case handling for catalog checks.

SQLite does not apply Unicode case folding to unquoted SQL identifiers.
This function must not be used to rewrite executable SQL or database names.
"""
from __future__ import annotations

_ASCII_UPPER_TO_LOWER = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
)


def sqlite_identifier_key(name: str) -> str:
    """A comparison key matching SQLite ASCII identifier-insensitivity."""
    if type(name) is not str:
        raise TypeError("INVALID_SQLITE_IDENTIFIER")
    return name.translate(_ASCII_UPPER_TO_LOWER)
