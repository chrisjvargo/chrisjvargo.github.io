from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from build import extract_body_html


class SiteShellTests(unittest.TestCase):
    def test_pandoc_fragment_html_is_accepted(self) -> None:
        fragment = "<h1 id=\"education\">Education</h1><p>Degree row</p>"
        self.assertEqual(extract_body_html(fragment), fragment)

    def test_non_html_text_is_not_treated_as_cv_html(self) -> None:
        self.assertIsNone(extract_body_html("plain text without document markup"))

    def test_full_html_body_is_extracted(self) -> None:
        html = "<html><body><h1 id=\"education\">Education</h1></body></html>"
        self.assertEqual(extract_body_html(html), "<h1 id=\"education\">Education</h1>")


if __name__ == "__main__":
    unittest.main()
