from pathlib import Path
import csv
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dv.load_release import load_release


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = Path(__file__).resolve().parents[2]
        cls.release = load_release(cls.repo / "data" / "dv_public_release")

    def test_release_has_manifest_and_hashes(self) -> None:
        self.assertEqual(self.release["release"]["release_id"], "bcdv-public-status-2026-06-24")
        self.assertTrue((self.repo / "data" / "dv_public_release" / "SHA256SUMS").exists())

    def test_all_claims_have_denominators(self) -> None:
        for claim in self.release["claims"]:
            with self.subTest(claim_id=claim.get("claim_id")):
                self.assertIn("denominator", claim)
                if str(claim.get("estimate_type", "")).lower() not in {"qualitative status", "status"}:
                    self.assertNotEqual(str(claim.get("denominator", "")).strip(), "")

    def test_hypothesis_verification_does_not_confirm_unverified_assertion(self) -> None:
        statuses = {row["support_status"] for row in self.release["hypotheses"]}
        self.assertEqual(statuses, {"unresolved_required_data_unavailable"})

    def test_evidence_gap_register_is_public_and_hashed(self) -> None:
        release_dir = self.repo / "data" / "dv_public_release"
        rel_path = "public_tables/evidence_gap_register.csv"
        self.assertTrue((release_dir / rel_path).exists())
        sha_manifest = (release_dir / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertIn(f"  {rel_path}", sha_manifest)
        self.assertEqual(len(self.release["public_tables"]["evidence_gap_register.csv"]), 14)

    def test_evidence_gap_request_files_exist_and_are_hashed(self) -> None:
        release_dir = self.repo / "data" / "dv_public_release"
        sha_manifest = (release_dir / "SHA256SUMS").read_text(encoding="utf-8")
        with (release_dir / "public_tables" / "evidence_gap_register.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        request_files = {
            item.strip()
            for row in rows
            for item in row["request_files"].split(";")
            if item.strip().startswith("records_requests/")
        }
        self.assertGreaterEqual(len(request_files), 14)
        for rel_path in sorted(request_files):
            with self.subTest(rel_path=rel_path):
                self.assertTrue((release_dir / rel_path).exists())
                self.assertIn(f"  {rel_path}", sha_manifest)

    def test_records_request_dispatch_matrix_is_public_hashed_and_unsent(self) -> None:
        release_dir = self.repo / "data" / "dv_public_release"
        rel_path = "public_tables/records_request_dispatch_matrix.csv"
        self.assertTrue((release_dir / rel_path).exists())
        sha_manifest = (release_dir / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertIn(f"  {rel_path}", sha_manifest)
        with (release_dir / rel_path).open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 20)
        self.assertTrue(any(row["linked_hypotheses"] for row in rows))
        self.assertEqual(
            {row["transmission_status"] for row in rows},
            {"not_transmitted_requires_user_authorization"},
        )

    def test_records_request_submission_channels_are_public_hashed_and_unsent(self) -> None:
        release_dir = self.repo / "data" / "dv_public_release"
        rel_path = "public_tables/records_request_submission_channels.csv"
        self.assertTrue((release_dir / rel_path).exists())
        sha_manifest = (release_dir / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertIn(f"  {rel_path}", sha_manifest)
        with (release_dir / rel_path).open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 20)
        self.assertEqual(
            {row["transmission_status"] for row in rows},
            {"not_transmitted_requires_user_authorization"},
        )
        self.assertTrue(all(row["source_verification_date"] == "2026-06-26" for row in rows))
        self.assertTrue(any(row["official_submission_url"].startswith("https://") for row in rows))
        self.assertTrue(any(row["channel_status"] == "multi_custodian_manual_verification_required" for row in rows))


if __name__ == "__main__":
    unittest.main()
