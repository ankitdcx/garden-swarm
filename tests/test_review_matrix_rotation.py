from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.matrix_repo_review import bounded_repo_pack, build_bundle, load_matrix as load_repo_matrix
from tools.rotate_design_review_target import select_target


ROOT = Path(__file__).resolve().parents[1]


class ReviewMatrixRotationTests(unittest.TestCase):
    def test_hourly_design_targets_rotate(self):
        matrix = json.loads((ROOT / 'agents/design-review-matrix.json').read_text(encoding='utf-8'))
        first = select_target(copy.deepcopy(matrix), 0)
        second = select_target(copy.deepcopy(matrix), 1)
        self.assertNotEqual(first['target_id'], second['target_id'])
        self.assertGreaterEqual(len(matrix['targets']), 2)
        self.assertGreaterEqual(int(matrix['minimum_independent_reviewer_families']), 3)

    def test_repo_bootstrap_target_is_bounded_and_resolvable(self):
        matrix, target, slot = load_repo_matrix(ROOT, 0)
        self.assertEqual(slot, 0)
        self.assertEqual(target['target_id'], 'RRM-BOOTSTRAP-REVIEW-SCHEDULER')
        self.assertGreaterEqual(int(matrix['minimum_independent_reviewer_families']), 3)
        source, trace = bounded_repo_pack(ROOT, target)
        self.assertTrue(source)
        self.assertTrue(trace)
        self.assertTrue(all(row['coverage'] in {'FULL', 'BOUNDED_HEAD_TAIL'} for row in trace))

    def test_repo_bundle_fails_closed_below_three_families(self):
        matrix, target, _ = load_repo_matrix(ROOT, 0)
        finding = {'reviewer_family': 'a'}
        bundle = build_bundle(
            matrix=matrix,
            target=target,
            day_slot=0,
            trace=[{'source':'x'}],
            independent=[finding, {'reviewer_family':'b'}],
            finals=[],
            attempts=[{'status':'CALLED','usage':{'cost':0}}],
        )
        self.assertEqual(bundle['status'], 'INSUFFICIENT_INDEPENDENT_REVIEW')
        self.assertFalse(bundle['semantic_delta_admitted'])

    def test_repo_bundle_can_only_reach_review_complete_after_three_final_families_and_zero_cost(self):
        matrix, target, _ = load_repo_matrix(ROOT, 0)
        independent = [{'reviewer_family': x} for x in ('a','b','c')]
        finals = [{'reviewer_family': x} for x in ('a','b','c')]
        attempts = [{'status':'CALLED','usage':{'cost':0}} for _ in range(6)]
        bundle = build_bundle(
            matrix=matrix,
            target=target,
            day_slot=0,
            trace=[{'source':'x'}],
            independent=independent,
            finals=finals,
            attempts=attempts,
        )
        self.assertEqual(bundle['status'], 'REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR')
        self.assertTrue(bundle['zero_cost_verified'])
        self.assertFalse(bundle['semantic_delta_admitted'])


if __name__ == '__main__':
    unittest.main()
