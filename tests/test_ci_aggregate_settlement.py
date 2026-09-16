import copy
import unittest

from tools.aggregate_ci_receipts import MANDATORY, aggregate


class CIAggregateSettlementTests(unittest.TestCase):
    def rows(self):
        return [
            {
                'id': i + 1,
                'run_attempt': 1,
                'head_sha': 'a' * 40,
                'path': path,
                'repository': {'full_name': 'owner/repo'},
                'event': 'pull_request',
                'status': 'completed',
                'conclusion': 'success',
                'html_url': f'https://example.invalid/{i + 1}',
            }
            for i, path in enumerate(MANDATORY)
        ]

    def result(self, rows):
        return aggregate(rows, head_sha='a' * 40, repository='owner/repo')

    def test_missing_lane_is_deferred_not_final_failure(self):
        rows = self.rows()[:-1]
        rows[0]['conclusion'] = 'failure'
        receipt = self.result(rows)
        self.assertEqual(receipt['overall'], 'UNKNOWN')
        self.assertFalse(receipt['settled'])
        self.assertEqual(receipt['deferred_reason'], 'MANDATORY_WORKFLOW_SET_NOT_SETTLED')

    def test_inflight_new_attempt_defers_even_if_old_attempt_passed(self):
        rows = self.rows()
        new = copy.deepcopy(rows[0])
        new.update(id=100, run_attempt=2, status='in_progress', conclusion=None)
        receipt = self.result(rows + [new])
        self.assertEqual(receipt['overall'], 'UNKNOWN')
        self.assertFalse(receipt['settled'])

    def test_settled_failure_fails_closed(self):
        rows = self.rows()
        rows[1]['conclusion'] = 'failure'
        receipt = self.result(rows)
        self.assertTrue(receipt['settled'])
        self.assertEqual(receipt['overall'], 'FAIL')
        self.assertIsNone(receipt['deferred_reason'])

    def test_settled_all_pass(self):
        receipt = self.result(self.rows())
        self.assertTrue(receipt['settled'])
        self.assertEqual(receipt['overall'], 'PASS')
        self.assertIsNone(receipt['deferred_reason'])


if __name__ == '__main__':
    unittest.main()
