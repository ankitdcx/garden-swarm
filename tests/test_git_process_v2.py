import hashlib,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from tools import check_git_preflight_event as preflight
from tools import render_git_operating_context as render
from tools import secret_scan
from tools import chatgpt_workstream as workstream
ROOT=Path(__file__).resolve().parents[1]
class GitProcessV2Tests(unittest.TestCase):
 def test_source_revision_generated_views_and_mirror_receipt(self):
  data,sha=render.canonical_source(ROOT/'GIT_OPERATING_CONTEXT_SOURCE.json'); self.assertEqual(data['schema'],'GardenGitOperatingContextSource/v2'); self.assertGreaterEqual(data['document_revision'],2); machine,human=render.render(ROOT/'GIT_OPERATING_CONTEXT_SOURCE.json'); self.assertEqual((ROOT/'GIT_OPERATING_CONTEXT.json').read_text(),machine); self.assertEqual((ROOT/'GIT_OPERATING_CONTEXT.md').read_text(),human); receipt=json.loads((ROOT/'GIT_OPERATING_CONTEXT_MIRROR_RECEIPT.json').read_text()); self.assertEqual(receipt['source_sha256'],sha); self.assertEqual(receipt['document_revision'],data['document_revision'])
 def test_bad_merge_recovery_never_rewrites_main(self):
  source=json.loads((ROOT/'GIT_OPERATING_CONTEXT_SOURCE.json').read_text()); self.assertTrue(source['recovery']['bad_merge']['never_reset_or_force_push_main'])
 def test_secret_scan_detects_constructed_token_without_disclosing_it(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x.txt'; token='sk-'+('B'*30); p.write_text('api_key = "'+token+'"\n'); receipt=secret_scan.scan_paths(['x.txt'],root=Path(td),allowlist=[]); self.assertEqual(receipt['status'],'BLOCKED'); self.assertNotIn(token,json.dumps(receipt))
 def test_lifecycle_marks_abandoned_without_delete_authority(self):
  policy=json.loads((ROOT/'CHATGPT_WORKSTREAM_POLICY.json').read_text()); base={'schema':workstream.SCHEMA,'workstream_id':'ws:a','work_package_id':'pkg:a','branch':'chatgpt/a','base_sha':'a'*40,'dependency_intent_ids':[],'integration_strategy':'INTEGRATION_BRANCH_IF_COLLISION','draft_pr_created_before_substantial_edit':True,'draft_opened_at':'2026-09-01T00:00:00Z','last_activity_at':'2026-09-01T00:00:00Z','status':'ACTIVE'}; self.assertEqual(workstream.lifecycle_status(base,now=datetime(2026,9,16,tzinfo=timezone.utc),policy=policy),'ABANDONED_REVIEW_REQUIRED'); self.assertTrue(policy['lifecycle']['stale_or_abandoned_is_not_delete_authority'])
 def test_preflight_revision_two_hash_binding(self):
  raw=(ROOT/'GIT_OPERATING_CONTEXT_SOURCE.json').read_bytes(); source=json.loads(raw); sha=hashlib.sha256(raw).hexdigest(); ws={'schema':'GardenChatGPTWorkstreamIntent/v1','workstream_id':'chatgpt:w','work_package_id':'WP','branch':'chatgpt/x','base_sha':'1'*40,'dependency_intent_ids':[],'integration_strategy':'INTEGRATION_BRANCH_IF_COLLISION','draft_pr_created_before_substantial_edit':True,'status':'ACTIVE'}; receipt={'schema':'GardenGitPreflightReceipt/v1','workstream_id':'chatgpt:w','repository':'ankitdcx/garden-swarm','base_sha':'1'*40,'git_context_revision':2,'git_context_source_sha256':sha,'process_pointer':'ankitdcx/garden-main:governance/PROCESS_CURRENT.json','process_version':'1.4','verified_merge_ruleset_id':23543047,'overlap_checked_open_prs':[],'overlap_result':'NO_MATERIAL_COLLISION_WITH_DECLARED_SCOPE','created_before_substantial_edit':True,'authority_effect':'NONE'}; body=preflight.WORKSTREAM_MARKER+'\n```json\n'+json.dumps(ws)+'\n```\n'+preflight.PREFLIGHT_MARKER+'\n```json\n'+json.dumps(receipt)+'\n```\n'; event={'repository':{'full_name':'ankitdcx/garden-swarm'},'pull_request':{'head':{'ref':'chatgpt/x'},'base':{'sha':'1'*40},'body':body}}; self.assertEqual(preflight.validate_event(event,source,sha)['status'],'PASS')
if __name__=='__main__': unittest.main()
