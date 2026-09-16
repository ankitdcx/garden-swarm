import copy,unittest
from datetime import datetime,timezone
from tools import chatgpt_workstream as w
BASE='a'*40
POLICY={
 'schema':'GardenChatGPTWorkstreamPolicy/v1','policy_revision':2,
 'workstream_intent_required_fields':['workstream_id','work_package_id','branch','base_sha','dependency_intent_ids','integration_strategy','draft_pr_created_before_substantial_edit','status','draft_opened_at','last_activity_at'],
 'allowed_status':['ACTIVE','REVALIDATE_REQUIRED','INTEGRATING','STALE_DRAFT','ABANDONED_REVIEW_REQUIRED','SUPERSEDED','CLOSED'],
 'allowed_integration_strategy':['DIRECT_IF_NO_COLLISION','INTEGRATION_BRANCH_IF_COLLISION'],
 'rules':{'future_chatgpt_branch_prefix':'chatgpt/','integration_branch_prefix':'integration/'},
 'collision_rule':{},
 'lifecycle':{'stale_draft_after_hours_without_activity':72,'abandoned_review_after_days_without_activity':14},
 'merge_train':{'driver':'EXTERNAL_CHATGPT_FRONTIER_OR_EXPLICIT_HUMAN_TRIGGER','scheduling':'EVENT_DRIVEN_NOT_CLOCK_DRIVEN','exit_condition':'ALL_WORKSTREAMS_MERGED_SUPERSEDED_CLOSED_OR_EXPLICITLY_BLOCKED_WITH_RECEIPT'}
}
def record(name,path,domain,deps=None,strategy='INTEGRATION_BRANCH_IF_COLLISION',activity='2026-09-16T00:00:00Z'):
 intent_id=f'chatgpt:{name}'
 return {'workstream':{'schema':w.SCHEMA,'workstream_id':f'ws:{name}','work_package_id':f'pkg:{name}','branch':f'chatgpt/{name}','base_sha':BASE,'dependency_intent_ids':deps or [],'integration_strategy':strategy,'draft_pr_created_before_substantial_edit':True,'draft_opened_at':activity,'last_activity_at':activity,'status':'ACTIVE'},'agent_intent':{'schema':'AgentWorkIntent/v1','intent_id':intent_id,'agent_id':'ChatGPT-test-lane','task_id':f'task:{name}','base_sha':BASE,'target_paths':[path],'target_symbols':[],'semantic_domains':[domain],'affected_invariants':[],'affected_contracts':[],'intended_effect':name,'parallel_mode':'COORDINATED'}}
class ChatGPTWorkstreamTests(unittest.TestCase):
 def test_early_draft_and_unique_branch_required(self):
  row=record('a','a.txt','A'); row['workstream']['draft_pr_created_before_substantial_edit']=False
  with self.assertRaisesRegex(ValueError,'early draft PR'): w.validate_workstream(row['workstream'],POLICY)
  row=record('a','a.txt','A'); row['workstream']['branch']='feature/a'
  with self.assertRaisesRegex(ValueError,'chatgpt/'): w.validate_workstream(row['workstream'],POLICY)
 def test_different_files_same_domain_need_integration(self):
  plan=w.plan([record('a','a.json','MODEL_ROUTING'),record('b','b.py','MODEL_ROUTING')],POLICY,now=datetime(2026,9,16,1,tzinfo=timezone.utc)); self.assertEqual(plan['integration_groups'][0]['status'],'INTEGRATION_BRANCH_REQUIRED'); self.assertEqual(plan['merge_train'],[])
 def test_dependency_order_and_driver(self):
  a=record('a','a.txt','A'); b=record('b','b.txt','B',deps=['chatgpt:a']); plan=w.plan([b,a],POLICY,now=datetime(2026,9,16,1,tzinfo=timezone.utc)); self.assertEqual(plan['merge_train'],['ws:a','ws:b']); self.assertEqual(plan['driver'],'EXTERNAL_CHATGPT_FRONTIER_OR_EXPLICIT_HUMAN_TRIGGER')
 def test_shared_branch_rejected(self):
  a=record('a','a.txt','A'); b=record('b','b.txt','B'); b['workstream']['branch']=a['workstream']['branch']
  with self.assertRaisesRegex(ValueError,'share a branch'): w.plan([a,b],POLICY,now=datetime(2026,9,16,1,tzinfo=timezone.utc))
 def test_abandoned_is_blocked_from_train(self):
  a=record('a','a.txt','A',activity='2026-09-01T00:00:00Z'); plan=w.plan([a],POLICY,now=datetime(2026,9,16,tzinfo=timezone.utc)); self.assertEqual(plan['blocked_lifecycle'][0]['status'],'ABANDONED_REVIEW_REQUIRED'); self.assertEqual(plan['merge_train'],[])
 def test_invalidation_sets_revalidate(self):
  merged=record('a','a.txt','MODEL_ROUTING')['agent_intent']; b=record('b','b.txt','MODEL_ROUTING'); events=w.dependency_invalidations(merged,[b]); self.assertEqual(events[0]['new_status'],'REVALIDATE_REQUIRED')
if __name__=='__main__': unittest.main()
