"""Synthetic structural tests for the metadata-only CycloneDX candidate."""
from email.message import Message
from types import SimpleNamespace
import unittest

from scripts.dependency_sbom import create_bom, _direct_install_groups


def _distribution(name, version, *, license_expression=None, license_text=None, classifiers=()):
    metadata = Message()
    metadata["Name"] = name
    metadata["Version"] = version
    if license_expression is not None:
        metadata["License-Expression"] = license_expression
    if license_text is not None:
        metadata["License"] = license_text
    for classifier in classifiers:
        metadata["Classifier"] = classifier
    return SimpleNamespace(metadata=metadata)


class DependencySbomTests(unittest.TestCase):
    def test_cyclonedx_records_direct_group_and_declared_expression_only(self):
        bom = create_bom(
            [
                _distribution("demo_lib", "1.2.3", license_expression="MIT"),
                _distribution("transitive-lib", "4.5", classifiers=(
                    "License :: OSI Approved :: BSD License",
                )),
            ],
            project_name="DBVORA",
            project_version="0.2.0",
            direct_groups={"demo-lib": ["ui"]},
            profile="ui,postgres,test",
            timestamp="2026-11-15T00:00:00Z",
        )
        self.assertEqual(bom["bomFormat"], "CycloneDX")
        self.assertEqual(bom["specVersion"], "1.6")
        self.assertEqual(bom["metadata"]["timestamp"], "2026-11-15T00:00:00Z")
        self.assertEqual(bom["metadata"]["component"]["purl"], "pkg:pypi/dbvora@0.2.0")
        demo = next(item for item in bom["components"] if item["name"] == "demo_lib")
        self.assertEqual(demo["purl"], "pkg:pypi/demo-lib@1.2.3")
        self.assertEqual(demo["licenses"], [{"expression": "MIT"}])
        self.assertEqual(demo["properties"][0]["value"], "ui")
        self.assertEqual(demo["properties"][2]["value"], "metadata-only-unverified")
        transitive = next(item for item in bom["components"] if item["name"] == "transitive-lib")
        self.assertEqual(transitive["licenses"], [{"license": {"name": "BSD License"}}])
        self.assertEqual(transitive["properties"][0]["value"], "resolved-transitive-or-tooling")

    def test_missing_license_metadata_is_explicit_and_requirement_groups_are_read(self):
        bom = create_bom(
            [_distribution("no-license", "0.1")],
            project_name="DBVORA",
            project_version="0.2.0",
        )
        item = bom["components"][0]
        self.assertEqual(item["licenses"], [
            {"license": {"name": "UNSPECIFIED (package metadata missing)"}}
        ])
        self.assertEqual(item["properties"][1]["value"], "missing")
        project = {
            "project": {
                "dependencies": ["core-lib>=1"],
                "optional-dependencies": {
                    "ui": ["FastAPI>=0.1"],
                    "postgres": ["psycopg[binary]>=3"],
                },
            }
        }
        self.assertEqual(_direct_install_groups(project), {
            "core-lib": ["core"],
            "fastapi": ["ui"],
            "psycopg": ["postgres"],
        })


if __name__ == "__main__":
    unittest.main()
