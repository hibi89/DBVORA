"""Windows-owner-only executable entry: synthetic SQLite HTML demo, no user DB.

This preview deliberately exposes no customer path option, archive operation,
network connection, unattended scheduler, or release claim.
"""
from __future__ import annotations

from dbvora.demo_preview import main


if __name__ == "__main__":
    raise SystemExit(main())
