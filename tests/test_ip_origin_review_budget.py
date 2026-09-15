import math
import unittest

from tools import run_ip_origin_multi_agent_review as review


class IPOriginReviewBudgetTests(unittest.TestCase):
    def test_151_record_backfill_fits_64_calls_with_four_families(self):
        batches = math.ceil(151 / review.BATCH_SIZE)
        self.assertEqual(review.BATCH_SIZE, 20)
        self.assertEqual(batches, 8)
        self.assertEqual(batches * 4 * 2, 64)
        self.assertLessEqual(review.WORKFLOW_COST_CEILING_USD, 0.80)

    def test_four_specialist_roles_exist(self):
        self.assertEqual(len(review.ROLE_PROMPTS), 4)
        self.assertEqual(
            {row[0] for row in review.ROLE_PROMPTS},
            {"novelty_prior_art", "patent_scope", "copyright_other_rights", "duplicate_lineage"},
        )


if __name__ == "__main__":
    unittest.main()
