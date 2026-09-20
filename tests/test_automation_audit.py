import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.aggregate_ci_receipts import aggregate, MANDATORY
from tools.coordinator_status import evaluate
from tools.constitutional_path_coverage import evaluate as coverage

ROOT = Path(__file__).resolve().parents[1]
ONE_USE_AUTHORIZED_WORKFLOW = 'one-use-final-ip-origin-review.yml'
ONE_USE_MARKER = 'HUMAN_AUTHORIZED_ONE_USE_IP_FINAL_REVIEW_20260915'
ONE_USE_TITLE = "Finalize Garden IP origin inventory review"


class AutomationAuditTests(unittest.TestCase):
    def test_every_provider_workflow_is_dispatch_only_and_guarded_before_secret(self):
        for path in (ROOT/'.github/workflows').glob('*.yml'):
            text = path.read_text()
            if 'OPENROUTER_API_KEY' not in text and 'GEMINI_API_KEY' not in text:
                continue
            with self.subTest(workflow=path.name):
                triggers = text.split('\non:\n',1)[1].split('\npermissions:',1)[0]
                self.assertNotIn('push:',triggers)
                self.assertNotIn('schedule:',triggers)
                if path.name == ONE_USE_AUTHORIZED_WORKFLOW:
                    self.assertIn('pull_request:',triggers)
                    self.assertIn(ONE_USE_MARKER,text)
                    self.assertIn(f"github.event.pull_request.title == '{ONE_USE_TITLE}'",text)
                    self.assertIn('github.event.pull_request.head.repo.full_name == github.repository',text)
                    self.assertIn('group: garden-ip-final-one-use-review',text)
                    self.assertNotIn('GEMINI_API_KEY',text)
                    continue
                self.assertNotIn('pull_request:',triggers)
                self.assertIn('group: garden-provider-review',text)
                if 'tools.independent_branch_worker' in text:
                    self.assertIn('tools.independent_branch_preflight', text)
                    self.assertLess(text.index('tools.independent_branch_preflight'), text.index('OPENROUTER_API_KEY'))
                    self.assertIn('INDEPENDENT_BRANCH_CONVERGENCE_V1', text)
                else:
                    self.assertLess(text.index('tools.check_dispatch_admission'),text.index('OPENROUTER_API_KEY'))

    def test_dispatch_fails_before_provider_work(self):
        result = subprocess.run([sys.executable,'-m','tools.check_dispatch_admission'],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('DISPATCH_BLOCKED',result.stderr)

    def test_paused_is_not_healthy_and_stale_active_evidence_cannot_pass(self):
        now = datetime(2026,9,15,tzinfo=timezone.utc)
        record = {'schema':'CoordinatorStatusReceipt/v1','scheduler_state':'PAUSED'}
        self.assertEqual(evaluate(record,now=now),'PAUSED')
        record.update(scheduler_state='RUNNING', active_heartbeat_max_age_seconds=7200)
        self.assertEqual(evaluate(record,now=now),'UNKNOWN')
        record['last_successful_dispatch_at']=(now-timedelta(hours=3)).isoformat()
        self.assertEqual(evaluate(record,now=now),'STALE')
        record['last_successful_dispatch_at']=(now+timedelta(hours=1)).isoformat()
        self.assertEqual(evaluate(record,now=now),'UNKNOWN')

    def test_simple_paid_budget_and_execution_scope_are_explicit(self):
        policy=json.loads((ROOT/'agents/openrouter-paid-review-policy.json').read_text())
        self.assertEqual(policy['daily_openrouter_cost_ceiling_usd'],2)
        self.assertEqual(policy['routine_model_call_cost_ceiling_usd'],0.05)
        self.assertIn('DEPRECATED',policy['budget_pool_scope'])
        self.assertEqual(policy['balance_status'],'NOT_USED_BY_ACTIVE_GROUP_REVIEW_BUDGET_RULE')
        self.assertEqual(policy['free_swarm']['max_parallelism'],1)
        self.assertEqual(policy['execution_limits']['max_model_calls_per_dispatch'],1)

    def test_guard_dependency_gap_remains_migration_not_fake_approval(self):
        result=coverage(ROOT)
        self.assertEqual(result['status'],'MIGRATION_REQUIRED')
        self.assertIn('scripts/check_constitutional_change.py',result['missing_paths'])
        self.assertIn('.github/workflows/constitutional-path-guard.yml',result['missing_paths'])
        self.assertEqual(result['authority_effect'],'NONE')

    def test_published_denominator_is_not_review_completion(self):
        receipt=json.loads((ROOT/'evidence/automation-audit-2026-09-15/canonical-section-count.json').read_text())
        self.assertEqual(receipt['TOTAL'],sum(receipt[k] for k in ['TIER_A','TIER_B','TIER_C']))
        self.assertEqual(receipt['TOTAL'],sum(receipt[k] for k in ['QUALIFIED','STALE','UNREVIEWED']))
        self.assertEqual(receipt['QUALIFIED'],0)
        self.assertIs(receipt['sweep_completion_valid'],False)


class CIAggregationTests(unittest.TestCase):
    def runs(self):
        return [{'id':i+1,'run_attempt':1,'head_sha':'a'*40,'path':p,'repository':{'full_name':'owner/repo'},'event':'pull_request','status':'completed','conclusion':'success'} for i,p in enumerate(MANDATORY)]

    def result(self, rows):
        return aggregate(rows,head_sha='a'*40,repository='owner/repo')['overall']

    def test_every_mandatory_lane_must_pass_at_exact_head(self):
        rows=self.runs();self.assertEqual(self.result(rows),'PASS')
        self.assertEqual(self.result(rows[:-1]),'UNKNOWN')
        rows[0]['head_sha']='b'*40;self.assertEqual(self.result(rows),'UNKNOWN')
        rows=self.runs();rows[0]['conclusion']='failure';self.assertEqual(self.result(rows),'FAIL')

    def test_newer_failed_or_inflight_attempt_cannot_be_hidden_by_old_pass(self):
        rows=self.runs();new=copy.deepcopy(rows[0]);new.update(run_attempt=2,conclusion='failure')
        self.assertEqual(self.result(rows+[new]),'FAIL')
        new.update(status='in_progress',conclusion=None)
        self.assertEqual(self.result(rows+[new]),'UNKNOWN')

    def test_foreign_or_manual_success_cannot_satisfy_required_lane(self):
        rows=self.runs();rows[0]['repository']['full_name']='foreign/repo'
        self.assertEqual(self.result(rows),'UNKNOWN')
        rows=self.runs();rows[0]['event']='workflow_dispatch'
        self.assertEqual(self.result(rows),'UNKNOWN')


if __name__=='__main__': unittest.main()
