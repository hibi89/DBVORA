"""Offline catalog HTML JavaScript syntax and metric presentation contract."""
import json
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest

from scripts.pg_synthetic_acceptance import _Connection
from dbvora.connectors.postgres_reader import inspect_catalog
from dbvora.multi_engine_report import assemble_workspace, render_report


class PgHtmlScriptTests(unittest.TestCase):
    def setUp(self):
        self.catalog = inspect_catalog(_Connection(), include_statistics=True)
        self.workspace = assemble_workspace([self.catalog])
        self.page = render_report(self.workspace)

    def test_real_pg_metadata_is_embedded_as_json_and_has_relationships(self):
        open_tag = '<script type="application/json" id="catalog">'
        payload = self.page.split(open_tag, 1)[1].split('</script>', 1)[0]
        model = json.loads(payload)
        self.assertEqual(model["table_count"], 3)
        self.assertEqual(model["databases"][0]["relationships"][0]["from"], "public.events")
        events = next(x for x in model["databases"][0]["tables"]
                      if x["key"] == "public.events")
        self.assertEqual(events["statistics"]["estimated_dead_rows"], 2000)
        self.assertEqual(len(events["optimization_review"]["rules"]), 2)
        self.assertFalse(events["optimization_review"]["automatic_actions"])

    def test_view_storage_and_statistics_not_fabricated(self):
        view = next(x for x in self.workspace["databases"][0]["tables"]
                    if x["key"] == "public.event_view")
        self.assertIsNone(view["size_bytes"])
        self.assertEqual(view["statistics"]["status"], "unavailable")

    def test_csp_forbids_network_and_metadata_not_printed_as_html(self):
        self.assertIn("connect-src 'none'", self.page)
        self.assertIn("default-src 'none'", self.page)
        self.assertNotIn("postgresql://", self.page)
        self.assertNotIn("password=", self.page)
        self.assertIn("Estimated live rows", self.page)
        self.assertIn("manual only", self.page)

    def test_real_embedded_javascript_parses_using_node(self):
        if not shutil.which("node"):
            self.fail("NODE_REQUIRED_FOR_UI_SYNTAX_TEST")
        script = self.page.split("<script>\n", 1)[1].split("</script>", 1)[0]
        process = subprocess.run(["node", "--check", "-"], input=script.encode("utf-8"),
                                 capture_output=True, timeout=20, check=False)
        self.assertEqual(process.returncode, 0, "OFFLINE_UI_SCRIPT_INVALID")

    def test_postgres_extra_is_optional_not_core_dependency(self):
        root = Path(__file__).resolve().parents[1]
        conf = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(conf["project"].get("dependencies"), [])
        pg = conf["project"]["optional-dependencies"].get("postgres")
        self.assertEqual(pg, ["psycopg[binary]>=3.2,<4"])


if __name__ == "__main__":
    unittest.main()
