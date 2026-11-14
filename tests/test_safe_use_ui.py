"""Localized safe-use guidance and fail-closed inventory errors stay user-visible in Korean."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "dbvora" / "web" / "index.html").read_text("utf-8")
APP = (ROOT / "dbvora" / "web" / "app.js").read_text("utf-8")


class SafeUseUiTests(unittest.TestCase):
    def test_page_explains_read_scope_consent_and_restore_safety(self):
        self.assertIn('<html lang="ko">', HTML)
        self.assertIn('id="safety-guidance"', HTML)
        self.assertIn('aria-controls="safety-guidance-copy"', HTML)
        for phrase in ("실제 데이터 행", "원본 파일을 수정하지 않습니다",
                       "각각 버튼을 눌렀을 때만", "--synthetic-only",
                       "--accept-plaintext", "별도 출력 폴더", "암호화되지 않습니다"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, HTML)

    def test_inventory_failure_messages_are_localized_and_server_text_is_not_rendered(self):
        self.assertIn("const INVENTORY_UI_ERRORS", APP)
        for code in ("CATALOG_LIMIT", "CHANGED_DURING_READ", "DB_READ_FAILED",
                     "FILE_UNAVAILABLE", "TEMPORARY_UNAVAILABLE", "REQUEST_TIMEOUT",
                     "LOCAL_SERVER_UNAVAILABLE"):
            with self.subTest(code=code):
                self.assertIn(code + ":", APP)
        self.assertIn("INVENTORY_UI_ERRORS[code] || INVENTORY_UI_ERRORS.UNKNOWN", APP)
        self.assertNotIn("error?.message || '연결 실패'", APP)


if __name__ == "__main__":
    unittest.main()
