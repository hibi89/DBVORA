"""Emit a CycloneDX 1.6 candidate from installed Python package metadata only.

The result is a technical inventory, not a legal license determination. It excludes
package files, environment paths, dependency URLs, environment variables and secrets.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import re
import tomllib
import uuid

_MAX_LICENSE_TEXT = 256
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalise_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _clean_metadata_text(value: object) -> str:
    text = re.sub(r"[\r\n\t]+", " ", str(value)).strip()
    return text[:_MAX_LICENSE_TEXT]


def _license_metadata(metadata) -> tuple[list[dict], str]:
    expression = _clean_metadata_text(metadata.get("License-Expression", ""))
    if expression:
        return [{"expression": expression}], "License-Expression"
    classifiers = metadata.get_all("Classifier") or []
    license_classifiers = [
        _clean_metadata_text(" :: ".join(value.split(" :: ")[2:]))
        for value in classifiers
        if value.startswith("License :: ") and value.partition(" :: ")[2].strip()
    ]
    if license_classifiers:
        return [{"license": {"name": value}} for value in sorted(set(license_classifiers))], "Classifier"
    legacy = _clean_metadata_text(metadata.get("License", ""))
    if legacy:
        return [{"license": {"name": legacy}}], "License"
    return [{"license": {"name": "UNSPECIFIED (package metadata missing)"}}], "missing"


def _direct_install_groups(project: dict) -> dict[str, list[str]]:
    declaration = project.get("project", {})
    groups: dict[str, list[str]] = {}
    requirements = declaration.get("dependencies", [])
    if requirements:
        groups["core"] = requirements
    for group, values in declaration.get("optional-dependencies", {}).items():
        groups[group] = values
    direct: dict[str, list[str]] = {}
    for group, values in groups.items():
        for requirement in values:
            match = _REQUIREMENT_NAME.match(str(requirement))
            if match:
                name = _normalise_name(match.group(1))
                direct.setdefault(name, []).append(group)
    return direct


def create_bom(
    distributions,
    *,
    project_name: str,
    project_version: str,
    direct_groups: dict[str, list[str]] | None = None,
    profile: str = "unspecified",
    timestamp: str | None = None,
) -> dict:
    direct_groups = direct_groups or {}
    components = []
    seen = set()
    for distribution in distributions:
        metadata = distribution.metadata
        name = _clean_metadata_text(metadata.get("Name", ""))
        version = _clean_metadata_text(metadata.get("Version", ""))
        if not name or not version:
            raise ValueError("Installed distribution is missing Name or Version metadata.")
        normalized = _normalise_name(name)
        purl = f"pkg:pypi/{normalized}@{version}"
        if purl in seen:
            continue
        seen.add(purl)
        licenses, license_source = _license_metadata(metadata)
        groups = sorted(set(direct_groups.get(normalized, [])))
        components.append({
            "type": "library",
            "name": name,
            "version": version,
            "bom-ref": purl,
            "purl": purl,
            "licenses": licenses,
            "properties": [
                {"name": "dbvora:install-groups",
                 "value": ",".join(groups) if groups else "resolved-transitive-or-tooling"},
                {"name": "dbvora:license-metadata-source", "value": license_source},
                {"name": "dbvora:legal-status", "value": "metadata-only-unverified"},
            ],
        })
    components.sort(key=lambda item: (item["name"].lower(), item["version"]))
    now = timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    normalized_project = _normalise_name(project_name)
    application_purl = f"pkg:pypi/{normalized_project}@{project_version}"
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": [{"vendor": "DBVORA", "name": "dependency-sbom-candidate", "version": "1"}],
            "component": {
                "type": "application",
                "name": project_name,
                "version": project_version,
                "bom-ref": application_purl,
                "purl": application_purl,
                "properties": [
                    {"name": "dbvora:dependency-profile", "value": _clean_metadata_text(profile)},
                    {"name": "dbvora:legal-status", "value": "metadata-only-unverified"},
                ],
            },
        },
        "components": components,
    }


def build_current_bom(*, profile: str = "unspecified", project_file: Path | None = None) -> dict:
    project_file = project_file or Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(project_file.read_text(encoding="utf-8"))
    declaration = project.get("project", {})
    return create_bom(
        importlib.metadata.distributions(),
        project_name=declaration["name"],
        project_version=declaration["version"],
        direct_groups=_direct_install_groups(project),
        profile=profile,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="unspecified")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    serialized = json.dumps(build_current_bom(profile=args.profile), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
