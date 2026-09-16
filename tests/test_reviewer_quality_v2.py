import unittest
from tools import reviewer_quality as q
POLICY={'schema':'GardenReviewerQualityPolicy/v1','quality_dimensions':{'source_grounding':.22,'defect_precision':.16,'defect_recall_after_closure':.18,'context_handling':.16,'instruction_schema_compliance':.12,'unique_material_contribution':.10,'counterexample_quality':.06},'hard_failures':['FABRICATED_SOURCE_OR_EVIDENCE'],'lifecycle':{'states':['ACTIVE','DEGRADED','SHADOW_CHALLENGED','QUARANTINED'],'ordinary_window_minimum_receipts':8,'degrade_when_weighted_quality_below':.58,'quarantine_when_weighted_quality_below':.48},'shadow_replacement':{'minimum_shadow_packets':6,'minimum_weighted_quality_improvement':.08,'candidate_unique_contribution_floor_relative_to_incumbent':-.05}}
class ReviewerQualityV2Tests(unittest.TestCase):
 def test_degraded_and_quarantined_cannot_jump_active(self):
  for state in ('DEGRADED','QUARANTINED'):
   r=q.validate_transition(current_state=state,target_state='ACTIVE',policy=POLICY); self.assertFalse(r['allowed']); self.assertIn('DIRECT_RETURN_TO_ACTIVE_FORBIDDEN_USE_SHADOW_CHALLENGED',r['reasons'])
 def test_shadow_challenged_requires_benchmark_and_registry_pr(self):
  r=q.validate_transition(current_state='SHADOW_CHALLENGED',target_state='ACTIVE',policy=POLICY); self.assertFalse(r['allowed']); r=q.validate_transition(current_state='SHADOW_CHALLENGED',target_state='ACTIVE',shadow={'schema':q.SHADOW_SCHEMA,'qualified':True},registry_pr_declared=True,policy=POLICY); self.assertTrue(r['allowed'])
 def test_transition_proposal_routes_recovery_through_shadow(self):
  s={'slot_id':'S','model':'m','recommended_state':'ACTIVE'}; r=q.transition_proposal(s,current_state='DEGRADED',policy=POLICY); self.assertEqual(r['recommended_state'],'SHADOW_CHALLENGED')
if __name__=='__main__': unittest.main()
