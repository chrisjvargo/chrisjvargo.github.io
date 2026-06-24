from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dv.language_lint import lint_text


class LanguageLintTests(unittest.TestCase):
    def test_rejects_inflammatory_language(self) -> None:
        findings = lint_text("The system is rigged in a war on men.")
        self.assertTrue(findings)

    def test_allows_qualified_false_allegation_language(self) -> None:
        findings = lint_text(
            "The record does not establish false allegation, and no verified finding of false private allegation appears."
        )
        self.assertEqual(findings, [])

    def test_rejects_police_charged_shorthand(self) -> None:
        findings = lint_text("Police charged the defendant with an offense.")
        self.assertTrue(any("police charged" in f.lower() for f in findings))


if __name__ == "__main__":
    unittest.main()
