import math
import unittest

from tools import run_ip_origin_multi_agent_review as review


class IPOriginReviewBudgetTests(unittest.TestCase):
    def test_up_to_200_records_fit_48_calls_with_three_paid_families(self):
        self.assertEqual(review.BATCH_SIZE, 25)
        self.assertEqual(math.ceil(200 / review.BATCH_SIZE), 8)
        self.assertEqual(8 * 3 * 2, 48)
        self.assertLessEqual(review.WORKFLOW_COST_CEILING_USD, 0.80)

    def test_four_specialist_roles_exist(self):
        self.assertEqual(len(review.ROLE_PROMPTS), 4)
        self.assertEqual(
            {row[0] for row in review.ROLE_PROMPTS},
            {"novelty_prior_art", "patent_scope", "copyright_other_rights", "duplicate_lineage"},
        )

    def test_supplement_schema_is_part_of_combined_inventory(self):
        self.assertEqual(review.SUPPLEMENT.name, "IP_ORIGIN_SUPPLEMENT.json")

    def test_compact_specialist_schema_accepts_full_25_record_batch(self):
        expected = {f"C-{i:02d}" for i in range(25)}
        raw = {"r": [[rid, "U", "PC", "M"] for rid in sorted(expected)]}
        rows = review._validate_specialist(raw, expected)
        self.assertEqual(len(rows), 25)
        self.assertEqual({row["id"] for row in rows}, expected)
        self.assertTrue(all(row["origin_status"] == "ORIGIN_UNCERTAIN" for row in rows))

    def test_compact_cross_exam_schema_is_bounded_and_validated(self):
        expected = {"A", "B", "C"}
        raw = {"d": [["B", "likely prior art", "E", "CA", "H"]], "u": ["C"]}
        result = review._validate_cross(raw, expected)
        self.assertEqual(result["unresolved_ids"], ["C"])
        self.assertEqual(result["disputes"][0]["id"], "B")
        self.assertEqual(result["disputes"][0]["origin_status"], "LIKELY_PREEXISTING")

    def test_compact_schema_rejects_missing_ids(self):
        with self.assertRaisesRegex(ValueError, "missing ids"):
            review._validate_specialist({"r": [["A", "U", "", "L"]]}, {"A", "B"})

    def test_family_reasoning_transport_matches_endpoint_contract(self):
        self.assertEqual(review._reasoning_for_family("glm"), {"effort": "low"})
        for family in ("deepseek", "qwen"):
            self.assertEqual(review._reasoning_for_family(family), {"effort": "none"})

    def test_protection_code_normalization_accepts_harmless_delimiters(self):
        self.assertEqual(review._protection_codes("C,S,A"), ["C", "S", "A"])
        self.assertEqual(review._protection_codes("C S A"), ["C", "S", "A"])
        self.assertEqual(review._protection_codes(["C", "S", "A"]), ["C", "S", "A"])
        self.assertEqual(
            review._protection_codes(["COPYRIGHT_EXPRESSION", "PATENT_CANDIDATE"]),
            ["C", "P"],
        )

    def test_protection_code_normalization_still_rejects_unknown_tokens(self):
        with self.assertRaisesRegex(ValueError, "bad protection token"):
            review._protection_codes("C,X")

    def test_specialist_object_form_is_only_syntactic_normalization(self):
        result = review._validate_specialist(
            {"r": [{"id": "A", "origin": "ORIGIN_UNCERTAIN", "protections": "C,S", "confidence": "MEDIUM"}]},
            {"A"},
        )
        self.assertEqual(result[0]["origin_status"], "ORIGIN_UNCERTAIN")
        self.assertEqual(result[0]["protection_candidates"], ["COPYRIGHT_EXPRESSION", "TRADE_SECRET_CANDIDATE"])
        self.assertEqual(result[0]["confidence"], "MEDIUM")


if __name__ == "__main__":
    unittest.main()
