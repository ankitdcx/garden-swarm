"""Registered offline review-boundary check; PASS is not review qualification."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

INPUT_PATHS = ['agents/design-review-matrix.json', 'agents/openrouter-paid-review-policy.json', 'agents/runtime/design-target-selection.json', 'agents/runtime/free-selection.json', 'agents/outbox/hourly/design-review-bundle.json', 'agents/runtime/paid-selection.json', 'agents/outbox/hourly/paid-review-bundle.json', 'agents/outbox/hourly/gemini-review.json']

def verify(inputs: dict) -> dict:

    for field in ('actual_cost_usd', 'routine_hourly_cost_ceiling_usd'):
        value = inputs['agents/outbox/hourly/paid-review-bundle.json'][field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('invalid finite nonnegative cost: ' + field)
    import json
    matrix = inputs['agents/design-review-matrix.json']
    policy = inputs['agents/openrouter-paid-review-policy.json']
    target_selection = inputs['agents/runtime/design-target-selection.json']
    free_selection = inputs['agents/runtime/free-selection.json']
    free_bundle = inputs['agents/outbox/hourly/design-review-bundle.json']
    selection = inputs['agents/runtime/paid-selection.json']
    bundle = inputs['agents/outbox/hourly/paid-review-bundle.json']
    gemini = inputs['agents/outbox/hourly/gemini-review.json']
    minimum = int(matrix['minimum_independent_reviewer_families'])
    if not minimum >= 3:
        raise ValueError('boundary failed: minimum >= 3')
    if not free_selection['schema'] == 'GardenFreeModelSelection/v2':
        raise ValueError("boundary failed: free_selection['schema'] == 'GardenFreeModelSelection/v2'")
    if not len(free_selection['selected']) == int(policy['free_swarm']['distinct_families_per_hour']):
        raise ValueError("boundary failed: len(free_selection['selected']) == int(policy['free_swarm']['distinct_families_per_hour'])")
    if not len({row['family'] for row in free_selection['selected']}) == len(free_selection['selected']):
        raise ValueError("boundary failed: len({row['family'] for row in free_selection['selected']}) == len(free_selection['selected'])")
    if not all((row['model'].endswith(':free') for row in free_selection['selected'])):
        raise ValueError("boundary failed: all((row['model'].endswith(':free') for row in free_selection['selected']))")
    if not free_bundle['schema'] == 'GardenDesignReviewBundle/v1':
        raise ValueError("boundary failed: free_bundle['schema'] == 'GardenDesignReviewBundle/v1'")
    if not free_bundle['target']['target_id'] == target_selection['target_id']:
        raise ValueError("boundary failed: free_bundle['target']['target_id'] == target_selection['target_id']")
    if not free_bundle['semantic_delta_admitted'] is False:
        raise ValueError("boundary failed: free_bundle['semantic_delta_admitted'] is False")
    if not (free_bundle['zero_cost_verified'] is True or free_bundle['status'] in {'INSUFFICIENT_INDEPENDENT_REVIEW', 'INSUFFICIENT_PEER_CROSS_EXAMINATION'}):
        raise ValueError("boundary failed: free_bundle['zero_cost_verified'] is True or free_bundle['status'] in {'INSUFFICIENT_INDEPENDENT_REVIEW', 'INSUFFICIENT_PEER_CROSS_EXAMINATION'}")
    selected = selection['selected']
    expected_families = [row['family'] for row in policy['routine_reviewers']]
    if not selection['schema'] == 'GardenPaidModelSelection/v2':
        raise ValueError("boundary failed: selection['schema'] == 'GardenPaidModelSelection/v2'")
    if not [row['family'] for row in selected] == expected_families:
        raise ValueError("boundary failed: [row['family'] for row in selected] == expected_families")
    if not selection['approved_families'] == expected_families:
        raise ValueError("boundary failed: selection['approved_families'] == expected_families")
    if not len(set(expected_families)) == len(expected_families):
        raise ValueError('boundary failed: len(set(expected_families)) == len(expected_families)')
    if not all((not row['model'].endswith(':free') for row in selected)):
        raise ValueError("boundary failed: all((not row['model'].endswith(':free') for row in selected))")
    if not selection['provider_policy']['data_collection'] == 'deny':
        raise ValueError("boundary failed: selection['provider_policy']['data_collection'] == 'deny'")
    if not selection['daily_openrouter_cost_ceiling_usd'] == 1.0:
        raise ValueError("boundary failed: selection['daily_openrouter_cost_ceiling_usd'] == 1.0")
    if not selection['semantic_delta_admitted'] is False:
        raise ValueError("boundary failed: selection['semantic_delta_admitted'] is False")
    if not target_selection['schema'] == 'GardenDesignTargetSelectionReceipt/v1':
        raise ValueError("boundary failed: target_selection['schema'] == 'GardenDesignTargetSelectionReceipt/v1'")
    if not target_selection['selection_mode'] == 'DETERMINISTIC_HOURLY_ROUND_ROBIN':
        raise ValueError("boundary failed: target_selection['selection_mode'] == 'DETERMINISTIC_HOURLY_ROUND_ROBIN'")
    if not target_selection['target_id'] == matrix['active_target_id']:
        raise ValueError("boundary failed: target_selection['target_id'] == matrix['active_target_id']")
    if not target_selection['target_count'] == len(matrix['targets']):
        raise ValueError("boundary failed: target_selection['target_count'] == len(matrix['targets'])")
    if not target_selection['target_index'] == target_selection['hour_slot'] % target_selection['target_count']:
        raise ValueError("boundary failed: target_selection['target_index'] == target_selection['hour_slot'] % target_selection['target_count']")
    if not target_selection['design_epoch'] == matrix['design_epoch']:
        raise ValueError("boundary failed: target_selection['design_epoch'] == matrix['design_epoch']")
    if not target_selection['canonical_source_root_sha256'] == matrix['canonical_source_root_sha256']:
        raise ValueError("boundary failed: target_selection['canonical_source_root_sha256'] == matrix['canonical_source_root_sha256']")
    if not target_selection['semantic_delta_admitted'] is False:
        raise ValueError("boundary failed: target_selection['semantic_delta_admitted'] is False")
    if not bundle['schema'] == 'GardenPaidDesignReviewBundle/v1':
        raise ValueError("boundary failed: bundle['schema'] == 'GardenPaidDesignReviewBundle/v1'")
    if not bundle['target_id'] == target_selection['target_id']:
        raise ValueError("boundary failed: bundle['target_id'] == target_selection['target_id']")
    if not bundle['selected_families'] == expected_families:
        raise ValueError("boundary failed: bundle['selected_families'] == expected_families")
    if not bundle['actual_cost_usd'] <= bundle['routine_hourly_cost_ceiling_usd']:
        raise ValueError("boundary failed: bundle['actual_cost_usd'] <= bundle['routine_hourly_cost_ceiling_usd']")
    if not bundle['daily_openrouter_cost_ceiling_usd'] == 1.0:
        raise ValueError("boundary failed: bundle['daily_openrouter_cost_ceiling_usd'] == 1.0")
    if not bundle['semantic_delta_admitted'] is False:
        raise ValueError("boundary failed: bundle['semantic_delta_admitted'] is False")
    if not bundle['requires_separate_gemini_lane'] is True:
        raise ValueError("boundary failed: bundle['requires_separate_gemini_lane'] is True")
    if not bundle['requires_separate_chatgpt_lane'] is True:
        raise ValueError("boundary failed: bundle['requires_separate_chatgpt_lane'] is True")
    if not bundle['requires_cross_examination'] is True:
        raise ValueError("boundary failed: bundle['requires_cross_examination'] is True")
    if not bundle['status'] in {'PAID_BLIND_REVIEW_COMPLETE_PROPOSALS_ONLY', 'PARTIAL_PAID_REVIEW_PROPOSALS_ONLY', 'HOURLY_COST_CEILING_EXCEEDED'}:
        raise ValueError("boundary failed: bundle['status'] in {'PAID_BLIND_REVIEW_COMPLETE_PROPOSALS_ONLY', 'PARTIAL_PAID_REVIEW_PROPOSALS_ONLY', 'HOURLY_COST_CEILING_EXCEEDED'}")
    if gemini.get('schema') == 'GardenGeminiMatrixReviewReceipt/v1':
        if not gemini['target_id'] == target_selection['target_id']:
            raise ValueError("boundary failed: gemini['target_id'] == target_selection['target_id']")
        if not gemini['design_epoch'] == matrix['design_epoch']:
            raise ValueError("boundary failed: gemini['design_epoch'] == matrix['design_epoch']")
        if not gemini['canonical_source_root_sha256'] == matrix['canonical_source_root_sha256']:
            raise ValueError("boundary failed: gemini['canonical_source_root_sha256'] == matrix['canonical_source_root_sha256']")
        if not gemini['semantic_delta_admitted'] is False:
            raise ValueError("boundary failed: gemini['semantic_delta_admitted'] is False")
    else:
        if not gemini.get('schema') in {'GardenGeminiAvailabilityReceipt/v1', 'GardenGeminiAvailabilityReceipt/v2'}:
            raise ValueError("boundary failed: gemini.get('schema') in {'GardenGeminiAvailabilityReceipt/v1', 'GardenGeminiAvailabilityReceipt/v2'}")
        if not gemini.get('admission_status') == 'NO_MODEL_FINDING':
            raise ValueError("boundary failed: gemini.get('admission_status') == 'NO_MODEL_FINDING'")
    return {'target_id': target_selection['target_id'], 'free_families_selected': [row['family'] for row in free_selection['selected']], 'free_independent_families_completed': free_bundle['independent_reviewer_family_count'], 'free_cross_exam_families_completed': free_bundle['final_disposition_family_count'], 'paid_families_selected': expected_families, 'paid_families_completed': bundle['completed_families'], 'openrouter_actual_cost_usd': bundle['actual_cost_usd'], 'openrouter_hourly_cost_ceiling_usd': bundle['routine_hourly_cost_ceiling_usd'], 'openrouter_daily_cost_ceiling_usd': bundle['daily_openrouter_cost_ceiling_usd'], 'gemini_status': gemini.get('status') or (gemini.get('independent_finding') or {}).get('disposition'), 'semantic_admission_minimum_families': minimum, 'semantic_delta_admitted': False}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', default='agents/outbox/hourly/boundary-receipt.json')
    args = parser.parse_args()
    try:
        inputs = {p: json.loads((Path(args.root)/p).read_text()) for p in INPUT_PATHS}
        evidence = verify(inputs)
        receipt = {'schema':'ReviewBoundaryCheckReceipt/v1','check_id':'CHECK-REVIEW-BOUNDARIES-001','status':'PASS','evidence':evidence,'semantic_delta_admitted':False}
    except (ValueError, KeyError, TypeError, OSError) as exc:
        receipt = {'schema':'ReviewBoundaryCheckReceipt/v1','check_id':'CHECK-REVIEW-BOUNDARIES-001','status':'FAIL','reason':str(exc),'semantic_delta_admitted':False}
    output = Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt['status']=='PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
