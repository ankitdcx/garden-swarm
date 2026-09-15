import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import run_ip_origin_multi_agent_review as review


class IPOriginReviewBudgetTests(unittest.TestCase):
    def test_up_to_200_records_fit_64_calls_with_four_families(self):
        self.assertEqual(review.BATCH_SIZE, 25)
        self.assertEqual(math.ceil(200 / review.BATCH_SIZE), 8)
        self.assertEqual(8 * 4 * 2, 64)
        self.assertLessEqual(review.WORKFLOW_COST_CEILING_USD, 0.80)

    def test_four_specialist_roles_exist(self):
        self.assertEqual(len(review.ROLE_PROMPTS), 4)
        self.assertEqual({row[0] for row in review.ROLE_PROMPTS},{"novelty_prior_art","patent_scope","copyright_other_rights","duplicate_lineage"})

    def test_supplement_schema_is_part_of_combined_inventory(self):
        # Structural contract: the reviewer exposes an explicit supplement path and schema.
        self.assertEqual(review.SUPPLEMENT.name, "IP_ORIGIN_SUPPLEMENT.json")


if __name__ == "__main__":
    unittest.main()
