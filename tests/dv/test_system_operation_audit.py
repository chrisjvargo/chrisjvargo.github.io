from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from system_operation_audit import build_audit


class SystemOperationAuditTests(unittest.TestCase):
    def test_build_audit_distinguishes_passes_and_open_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            dist = repo / "dist"
            (dist / "cv").mkdir(parents=True)
            (dist / "dv").mkdir(parents=True)
            (dist / "assets").mkdir(parents=True)
            (dist / "build_report.json").write_text(
                json.dumps(
                    {
                        "cv_html_status": "pandoc_ok",
                        "cv_pdf_status": "compiled_with_latexmk",
                        "required_publication_metadata_gaps": 0,
                        "selected_publication_expected_pages": 3,
                        "selected_publication_detail_pages": 3,
                        "missing_abstracts": 2,
                        "unmatched_publications": 1,
                    }
                ),
                encoding="utf-8",
            )
            (repo / "PUBLICATION_METADATA_POLICY.md").write_text("policy", encoding="utf-8")
            (dist / "dv" / "dv_build_report.json").write_text(
                json.dumps({"hypothesis_status_counts": {"unresolved_required_data_unavailable": 14}}),
                encoding="utf-8",
            )
            (dist / "index.html").write_text(
                "\n".join(
                    [
                        "Google Cloud AI work",
                        "Research, teaching, and software for AI field readiness.",
                        "Ph.D., Mass Communication",
                        "Master of Arts, Advertising &amp; Public Relations",
                        "Bachelor of Arts, Advertising &amp; Public Relations",
                        "Field-readiness needs analysis",
                        "Seller-readiness transcript demo",
                        "LLM deployment courseware",
                        "socialcontext.ai",
                        "Inside a Social Media Brand Safety Algorithm",
                        "Toward a Tweet Typology",
                        "From Ads to Addiction",
                    ]
                ),
                encoding="utf-8",
            )
            (dist / "cv" / "index.html").write_text(
                '<h1 id="education">Education</h1><p>Master of Arts, Advertising &amp; Public Relations</p>',
                encoding="utf-8",
            )
            (dist / "assets" / "cv.pdf").write_bytes(b"%PDF")

            checks = {check.check_id: check for check in build_audit(repo, dist)}

        self.assertEqual(checks["OPS001"].status, "pass")
        self.assertEqual(checks["OPS002"].status, "pass")
        self.assertEqual(checks["OPS003"].status, "pass")
        self.assertEqual(checks["OPS005"].status, "open_gap")
        self.assertEqual(checks["OPS006"].status, "pass")


if __name__ == "__main__":
    unittest.main()
