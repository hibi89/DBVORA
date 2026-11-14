"""Guard the public README against unsupported performance claims."""
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UNSUPPORTED_PROVIDER_COMPARISON = re.compile(
    r"(?:PostgreSQL|Supabase).{0,100}"
    r"(?:better than|faster|cheaper|outperforms|superior|more efficient|"
    r"보다 빠르|보다 저렴|보다 우월|더 빠르|더 저렴|우월|이겼)"
    r"|(?:better than|faster|cheaper|outperforms|superior|more efficient|"
    r"보다 빠르|보다 저렴|보다 우월|더 빠르|더 저렴|우월|이겼)"
    r".{0,100}(?:PostgreSQL|Supabase)",
    re.IGNORECASE,
)


class PerformanceClaimBoundaryTests(unittest.TestCase):
    def test_public_readme_limits_runner_samples_and_provider_comparisons(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "CI의 합성 표본 수치는 고객 성능이나 운영 절감의 근거가 아니다.",
            readme,
        )
        self.assertIn(
            "PostgreSQL/Supabase와의 직접 성능 비교는 측정되지 않아 비교 불가다.",
            readme,
        )
        self.assertNotRegex(readme, r"[0-9]+(?:[.][0-9]+)?[ ]*%")
        self.assertIsNone(UNSUPPORTED_PROVIDER_COMPARISON.search(readme))


if __name__ == "__main__":
    unittest.main()
