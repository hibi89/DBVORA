"""Errors intended for local CLI/UI presentation without leaking source paths."""


class InventoryError(Exception):
    """Safe error with a stable public code and no private path or SQL data."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
