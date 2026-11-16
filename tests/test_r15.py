"""The comparison with the Release 1.5 baseline (tools/diff_r15.py) on the committed models."""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import diff_r15  # noqa: E402


@unittest.skipUnless((REPO / "prior" / "release-1.5" / "model" / "profiles.json").exists()
                     and (REPO / "model" / "profiles.json").exists(), "models not present")
class CompareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = diff_r15.compute(REPO)

    def find(self, element, aspect):
        return [r for r in self.res["rows"] if r["element"] == element and r["aspect"] == aspect]

    def test_usage_change_across_profiles_is_one_row(self):
        rows = self.find("PID-1", "usage")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["old"], rows[0]["new"], rows[0]["kind"]), ("R", "O", "loosened"))
        self.assertIn("Z22", rows[0]["profiles"])

    def test_not_allowed_to_allowed_is_loosened(self):
        self.assertEqual(self.find("MSA-5", "usage")[0]["kind"], "loosened")

    def test_value_sets_matched_by_code_system(self):
        rows = self.find("RXA-5", "binding")
        self.assertEqual((rows[0]["old"], rows[0]["new"]), ("CVX", "CVX, NDC"))

    def test_wrapper_group_collapsed(self):
        z31 = [r for r in self.res["rows"] if r["aspect"] == "segment" and "Z31" in r["profiles"]]
        self.assertFalse([r for r in z31 if "RESPONSE" in r["element"]])

    def statement(self, sid):
        return next(s for s in self.res["statements"] if s["id"] == sid)

    def test_statement_changed_by_assertion(self):
        s = self.statement("IZ-42")  # MSH-15: ER in Release 1.5, NE now
        self.assertEqual(s["status"], "changed")

    def test_statement_split_into_parts(self):
        s = self.statement("IZ-17")
        self.assertEqual((s["status"], s["new_id"]), ("split", "IZ-17a, IZ-17b, IZ-17c"))
        self.assertFalse([x for x in self.res["statements"] if x["id"] == "IZ-17a"])

    def test_wording_only_is_not_a_change(self):
        self.assertEqual(self.statement("IZ-12")["status"], "same")  # only "(Case Sensitive)" differs

    def test_external_codes_and_placeholders_not_compared(self):
        for c in self.res["code_changes"]:
            self.assertNotIn(c["value_set"], {"CVX", "MVX", "NDC"})
            self.assertNotIn("...", c["added"] + c["removed"])


if __name__ == "__main__":
    unittest.main()
