import copy
import json
from pathlib import Path
import unittest

from tools.verify_review_boundaries import verify

ROOT = Path(__file__).resolve().parents[1]


def valid_inputs():
    policy = json.loads((ROOT/'agents/openrouter-paid-review-policy.json').read_text())
    families = [r['family'] for r in policy['routine_reviewers']]
    free = [{'family':f,'model':f+'/m:free'} for f in families]
    selection = {'schema':'GardenPaidModelSelection/v2', 'selected':policy['routine_reviewers'],
                 'approved_families':families, 'provider_policy':{'data_collection':'deny'},
                 'daily_openrouter_cost_ceiling_usd':1.0, 'semantic_delta_admitted':False}
    return {
        'agents/design-review-matrix.json':{'minimum_independent_reviewer_families':3,'active_target_id':'target','targets':[{}], 'design_epoch':'v15.5','canonical_source_root_sha256':'source'},
        'agents/openrouter-paid-review-policy.json':policy,
        'agents/runtime/design-target-selection.json':{'schema':'GardenDesignTargetSelectionReceipt/v1','selection_mode':'DETERMINISTIC_HOURLY_ROUND_ROBIN','target_id':'target','target_count':1,'target_index':0,'hour_slot':0,'design_epoch':'v15.5','canonical_source_root_sha256':'source','semantic_delta_admitted':False},
        'agents/runtime/free-selection.json':{'schema':'GardenFreeModelSelection/v2','selected':free},
        'agents/outbox/hourly/design-review-bundle.json':{'schema':'GardenDesignReviewBundle/v1','target':{'target_id':'target'},'semantic_delta_admitted':False,'zero_cost_verified':True,'status':'REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR','independent_reviewer_family_count':4,'final_disposition_family_count':4},
        'agents/runtime/paid-selection.json':selection,
        'agents/outbox/hourly/paid-review-bundle.json':{'schema':'GardenPaidDesignReviewBundle/v1','target_id':'target','selected_families':families,'completed_families':families,'actual_cost_usd':0.01,'routine_hourly_cost_ceiling_usd':0.05,'daily_openrouter_cost_ceiling_usd':1.0,'semantic_delta_admitted':False,'requires_separate_gemini_lane':True,'requires_separate_chatgpt_lane':True,'requires_cross_examination':True,'status':'PAID_BLIND_REVIEW_COMPLETE_PROPOSALS_ONLY'},
        'agents/outbox/hourly/gemini-review.json':{'schema':'GardenGeminiAvailabilityReceipt/v2','admission_status':'NO_MODEL_FINDING','status':'UNAVAILABLE'},
    }


class ReviewBoundaryTests(unittest.TestCase):
    def test_valid_boundary_pass_is_not_semantic_admission(self):
        result = verify(valid_inputs())
        self.assertIs(result['semantic_delta_admitted'], False)
        self.assertEqual(result['gemini_status'], 'UNAVAILABLE')

    def test_rejects_real_boundary_violations(self):
        attacks = [
            ('agents/runtime/free-selection.json', lambda x: x['selected'][0].update(model='paid/model')),
            ('agents/runtime/free-selection.json', lambda x: x['selected'][0].update(family='qwen')),
            ('agents/runtime/paid-selection.json', lambda x: x['provider_policy'].update(data_collection='allow')),
            ('agents/outbox/hourly/paid-review-bundle.json', lambda x: x.update(target_id='other-cycle')),
            ('agents/outbox/hourly/paid-review-bundle.json', lambda x: x.update(semantic_delta_admitted=True)),
        ]
        for path, attack in attacks:
            inputs = valid_inputs(); attack(inputs[path])
            with self.subTest(path=path), self.assertRaises(ValueError):
                verify(inputs)

    def test_nonfinite_negative_boolean_costs_fail(self):
        for cost in (float('nan'), float('inf'), -1, True):
            inputs = valid_inputs()
            inputs['agents/outbox/hourly/paid-review-bundle.json']['actual_cost_usd'] = cost
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                verify(inputs)
