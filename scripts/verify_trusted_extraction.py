"""Read-only extracted ZIP audit from a separately trusted DBVORA checkout.

Run with installed Python -I -S -B and this script's absolute path.
Never import any module from the supplied extracted package before auditing it.
Unsigned SHA manifests detect mutation only, NOT publisher authenticity.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


class _NoInputLeakParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("INVALID_ARGUMENTS")


def check(extracted: Path, *, trusted_root: Path | None = None) -> dict:
    """Audit package files without executing any of the extracted source."""
    origin = trusted_root if trusted_root is not None else Path(__file__).resolve().parents[1]
    if not isinstance(extracted, Path) or not extracted.is_absolute():
        raise ValueError("ABSOLUTE_PACKAGE_PATH_REQUIRED")
    if not extracted.exists():
        raise ValueError("PACKAGE_UNAVAILABLE")
    # Reject using the trusted checkout as the candidate, or nesting the
    # untrusted candidate within it. Neither path must be user/customer data.
    origin = origin.resolve(strict=True)
    target = extracted.resolve(strict=True)
    if origin == target or origin in target.parents or target in origin.parents:
        raise ValueError("SEPARATE_TRUSTED_CHECKOUT_REQUIRED")
    verifier = origin / "dbvora" / "archive" / "portable_verify.py"
    if not verifier.is_file():
        raise ValueError("TRUSTED_VERIFIER_UNAVAILABLE")
    # Load by explicit trusted path, never from sys.path or the extracted tree.
    spec = importlib.util.spec_from_file_location("dbvora_trusted_portable_verify", verifier)
    if spec is None or spec.loader is None:
        raise ValueError("TRUSTED_VERIFIER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify(extracted)


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _NoInputLeakParser(add_help=False)
        parser.add_argument("--extracted", required=True)
        args = parser.parse_args(argv)
        result = check(Path(args.extracted))
    except ValueError as error:
        result = {"status": "FAIL_CLOSED", "error_code": str(error),
                  "customer_ready": False, "publisher_authenticity_verified": False}
    except Exception as error:
        # The verifier uses stable error codes; never emit exceptions/paths.
        code = str(error)
        if code not in {
            "INVALID_PACKAGE_ROOT", "UNSAFE_PACKAGE_ROOT", "PACKAGE_ROOT_UNAVAILABLE",
            "UNSAFE_PACKAGE_ENTRY", "PACKAGE_ENTRY_CHANGED", "PACKAGE_ENTRY_UNAVAILABLE",
            "INVALID_PACKAGE_MANIFEST", "PACKAGE_TOO_LARGE", "PACKAGE_DIGEST_MISMATCH",
            "PACKAGE_ENTRY_LIMIT", "PACKAGE_BYTECODE_PRESENT", "UNLISTED_PACKAGE_SOURCE",
        }:
            code = "TRUSTED_AUDIT_FAILURE"
        result = {"status": "FAIL_CLOSED", "error_code": code,
                  "customer_ready": False, "publisher_authenticity_verified": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS_UNSIGNED_EXTRACTED_CONTENTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
