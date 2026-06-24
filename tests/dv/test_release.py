from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
