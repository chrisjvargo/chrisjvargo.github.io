from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dv.privacy import scan_dist


class PrivacyScanTests(unittest.TestCase):
    def test_detects_personal_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("Contact jane.doe@example.com", encoding="utf-8")
            findings = scan_dist(root)
        self.assertTrue(any("email" in finding for finding in findings))

    def test_allows_generated_dv_release(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        dist = repo / "dist" / "dv"
        if not dist.exists():
            self.skipTest("dist has not been built")
        findings = scan_dist(dist)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
