"""Startup errors remain fixed, Korean and path-free for local UI users."""
from contextlib import redirect_stderr
import io
import json
import socket
import tempfile
from pathlib import Path
import unittest

from dbvora.serve import main
from tests.fixtures.make_sqlite import create_fixture


class ServeErrorTests(unittest.TestCase):
    def test_busy_port_reports_korean_fixed_code_without_database_path(self):
        with tempfile.TemporaryDirectory(prefix="dbvora-serve-synthetic-") as root:
            database = create_fixture(Path(root) / "fixture.sqlite")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                port = listener.getsockname()[1]
                error_stream = io.StringIO()
                with redirect_stderr(error_stream):
                    code = main(["--db", str(database), "--port", str(port)])
                self.assertEqual(code, 3)
            report = json.loads(error_stream.getvalue())
            self.assertEqual(report["error"]["code"], "PORT_IN_USE")
            self.assertIn("포트는 사용 중입니다", report["error"]["message"])
            self.assertNotIn(str(database), error_stream.getvalue())


if __name__ == "__main__":
    unittest.main()
