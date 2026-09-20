import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools import review_context as c
from tools import independent_branch_protocol as p
from tools import independent_branch_worker as w
from tools import single_review_worker as legacy
from tools.review_budget import effective_policy


class ContextReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        files = ['SOURCE_MANIFEST.json', 'agents/openrouter-paid-review-policy.json',
                 'agents/review-context-policy.json', 'agents/provider-exclusion-policy.json',
                 'agents/independent-branch-convergence-policy.json', 'agents/design-review-matrix.json']
        files += [r['path'] for r in json.loads(Path('SOURCE_MANIFEST.json').read_text())['canonical_files']]
        for file in files:
            dest = cls.root / file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, dest)
        cls.policy = json.loads((cls.root / files[1]).read_text())
        cls.target = json.loads((cls.root / 'agents/design-review-matrix.json').read_text())['targets'][0]
        from tools.matrix_design_review import extract_target
        cls.source, cls.trace = extract_target(cls.root, cls.target)
        cls.profile = c.select_profile(cls.policy, cls.target)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def packet(self, requests=None):
        return c.build_packet(self.root, self.target, self.source, self.trace, self.profile, requests)

    def bind_directive(self, directive):
        from tests.test_context_capsule import ContextCapsuleTests
        from tools import context_capsule
        cap = ContextCapsuleTests().capsule()
        cap['target_id'] = self.target['target_id']
        cap['source_identity'].update(
            canonical_source_root_sha256=self.packet()['source_root_sha256'],
            target_source=self.trace['source'], target_source_sha256=self.trace['source_sha256'])
        directive.update(architecture_context_capsule=cap,
                         architecture_context_capsule_sha256=context_capsule.sha256_value(cap),
                         same_context_capsule_for_all_reviewers=True)
        packet, _, _ = c.bind_capsule(self.packet(), directive, self.target, self.trace)
        directive['source_packet_sha256'] = packet['packet_sha256']
        directive['private_baseline_commitment']['source_packet_sha256'] = packet['packet_sha256']
        return directive

    def test_capsule_root_must_match_verified_five_file_corpus(self):
        from tests.test_context_capsule import ContextCapsuleTests
        from tools import context_capsule
        cap = ContextCapsuleTests().capsule()
        cap['target_id'] = self.target['target_id']
        cap['source_identity'].update(target_source=self.trace['source'], target_source_sha256=self.trace['source_sha256'])
        directive = {'architecture_context_capsule': cap,
                     'architecture_context_capsule_sha256': context_capsule.sha256_value(cap)}
        with self.assertRaisesRegex(ValueError, 'canonical root'):
            c.bind_capsule(self.packet(), directive, self.target, self.trace)

    def test_packet_has_all_five_sources_and_reproducible_exact_passages(self):
        first, second = self.packet(), self.packet()
        self.assertEqual(first, second)
        self.assertEqual(first['coverage']['indexed_files'], 5)
        self.assertFalse(first['coverage']['dependency_closure_proved'])
        self.assertGreater(first['coverage']['omitted_candidate_count'], 0)
        for excerpt in first['support_passages']:
            text = (self.root / excerpt['path']).read_text().splitlines(keepends=True)
            actual = ''.join(text[excerpt['start_line'] - 1:excerpt['end_line']])
            self.assertEqual(actual, excerpt['text'])
            self.assertEqual(c.text_hash(actual), excerpt['excerpt_sha256'])
        self.assertGreaterEqual(len({r['path'] for r in first['support_passages']}), 4)

    def test_tampered_index_is_rebuilt_and_reused_without_trusting_cache(self):
        manifest, docs = c.load_corpus(self.root)
        key, original, _ = c.index(self.root, manifest, docs)
        path = self.root / '.cache/garden-review' / ('index-' + key + '.json')
        saved = json.loads(path.read_text())
        saved['chunks'][0]['text'] = 'invented policy'
        path.write_text(json.dumps(saved))
        _, rebuilt, reused = c.index(self.root, manifest, docs)
        self.assertFalse(reused)
        self.assertEqual(original, rebuilt)
        self.assertTrue(c.index(self.root, manifest, docs)[2])

    def test_changed_canonical_bytes_block_context(self):
        path = self.root / self.target['source_file']
        old = path.read_bytes()
        try:
            path.write_bytes(old + b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                self.packet()
        finally:
            path.write_bytes(old)

    def test_requested_passage_is_included_and_changes_commitment(self):
        first = self.packet()
        cid = first['coverage']['omitted_candidate_ids'][0]
        second = self.packet([{'chunk_id': cid}])
        self.assertIn(cid, [r['chunk_id'] for r in second['support_passages']])
        self.assertNotEqual(first['packet_sha256'], second['packet_sha256'])
        with self.assertRaises(ValueError):
            self.packet([{'chunk_id': '../../secrets'}])

    def test_missing_query_is_not_reported_as_design_absence(self):
        result = self.packet([{'query': 'xyzzynonexistentmechanism'}])
        self.assertIn('xyzzynonexistentmechanism', result['coverage']['unresolved_queries'])
        self.assertFalse(result['coverage']['dependency_closure_proved'])

    def test_complexity_floors_and_provider_output_limits(self):
        self.assertEqual(self.profile['max_output_tokens'], 16000)
        with self.assertRaises(ValueError):
            c.select_profile(self.policy, self.target, 'ROUTINE')
        target = {**self.target, 'target_kind': 'theory'}
        profile = c.select_profile(self.policy, target)
        self.assertEqual(profile['max_output_tokens'], 32000)
        endpoint = {'tag': 'allowed', 'provider_name': 'Allowed', 'status': 0, 'context_length': 200000,
                    'supported_parameters': ['reasoning'], 'max_completion_tokens': 32000,
                    'pricing': {'prompt': '.00000005', 'completion': '.0000002'}}
        exclusions = json.loads((self.root / 'agents/provider-exclusion-policy.json').read_text())
        body, _ = legacy.endpoint_request(endpoint, self.policy['routine_reviewers'][0], 'public', legacy.money('.01'), self.policy, exclusions, profile=profile)
        self.assertEqual(body['reasoning']['effort'], 'high')
        self.assertEqual(body['max_tokens'], 32000)
        endpoint['max_completion_tokens'] = 8000
        with self.assertRaisesRegex(ValueError, 'output depth'):
            legacy.endpoint_request(endpoint, self.policy['routine_reviewers'][0], 'public', legacy.money('.1'), self.policy, exclusions, profile=profile)

    def test_audit_requires_current_dated_target_plan_and_preserves_pools(self):
        now = datetime(2026, 9, 16, tzinfo=timezone.utc).timestamp()
        normal, receipt = effective_policy(self.policy, {'target_id': 'T'}, now)
        self.assertEqual(normal['daily_openrouter_cost_ceiling_usd'], 2)
        self.assertEqual(receipt['per_call_usd'], '0.01')
        directive = {'target_id': 'T', 'spending_mode': 'AUDIT'}
        with self.assertRaises(ValueError):
            effective_policy(self.policy, directive, now)
        directive['audit_window'] = {'utc_day': '2026-09-16', 'target_id': 'T', 'audit_id': 'audit-1', 'purpose': 'cross-module audit'}
        audit, _ = effective_policy(self.policy, directive, now)
        self.assertEqual(audit['daily_openrouter_cost_ceiling_usd'], 2)
        self.assertEqual(audit['routine_model_call_cost_ceiling_usd'], 0.01)
        with self.assertRaises(ValueError):
            effective_policy(self.policy, directive, now + 86400)
        with self.assertRaisesRegex(ValueError, 'daily'):
            legacy.budget_check(
                {'paused': False, 'attempts': []},
                {'usage': 999, 'usage_daily': 1.995},
                audit,
                now,
            )

    def test_live_worker_uses_same_rich_packet_for_two_families_and_reserves_first(self):
        self.exercise_worker('SUFFICIENT')

    def test_material_context_gap_stops_before_second_reviewer(self):
        self.exercise_worker('EXPAND_REQUIRED')

    def exercise_worker(self, context_verdict):
        state = {'scope': 'PUBLIC_MATRIX_REVIEW_ONLY', 'paused': False, 'attempts': [], 'cycles': {}}
        saves, calls = [], []
        packet = self.packet()
        directive = {'schema': p.DIRECTIVE_SCHEMA, 'protocol': p.PROTOCOL_ID, 'public_only': True,
                     'target_id': self.target['target_id'], 'phase': 'BLIND', 'same_neutral_query_for_all_reviewers': True,
                     'source_packet_sha256': packet['packet_sha256'], 'reviewer_families': [r['family'] for r in self.policy['routine_reviewers']],
                     'private_baseline_commitment': {'schema': p.BASELINE_SCHEMA, 'baseline_sha256': 'b'*64,
                        'neutral_query_sha256': p.sha256_text(p.neutral_query(self.target)),
                        'source_packet_sha256': packet['packet_sha256'], 'created_before_openrouter_calls': True}}
        self.bind_directive(directive)
        class Ledger:
            def __init__(self, token): self.value = state
            def save(self, value): saves.append(copy.deepcopy(value))
        finding = {k: 'fixture' for k in ['current_semantic_claim','proposed_delta','do_nothing_comparison','uncertainty','evidence_ancestry','overturn_conditions']}
        finding.update(source_anchors=['CONSTITUTIONAL EVENTS'], falsification_attempts=['fixture'], evidence_search_trace=['source'], affected_invariants=[],affected_tests=[],affected_contracts=[],disposition='NO_CHANGE')
        finding.update(context_sufficiency=context_verdict, missing_context_reason='' if context_verdict == 'SUFFICIENT' else 'Need authority dependency', requested_dependency_or_source_refs=[] if context_verdict == 'SUFFICIENT' else ['AuthorityScope'])
        def http(url, token, body=None, **kwargs):
            if url.endswith('/models'):
                return {'data': [{'id': r['model'], 'canonical_slug': r['model']} for r in self.policy['routine_reviewers']]}
            if url.endswith('/key'):
                return {'data': {'usage': .001, 'usage_daily': .001}}
            if url.endswith('/endpoints'):
                return {'data': {'endpoints': [{'tag':'allowed','provider_name':'Allowed','status':0,'context_length':200000,'pricing':{'prompt':'.00000005','completion':'.0000002'}}]}}
            self.assertEqual(saves[-1]['attempts'][-1]['status'], 'RESERVED')
            calls.append(body)
            return {'id': 'fixture-' + str(len(calls)), 'model':body['model'],'provider':'Allowed','usage':{'cost':.005},'choices':[{'finish_reason':'stop','message':{'content':json.dumps(finding)}}]}
        env = {'OPENROUTER_API_KEY':'fixture','GH_REVIEW_TOKEN':'fixture','GITHUB_SHA':'fixture','GITHUB_RUN_ID':'fixture'}
        with patch.dict(w.os.environ, env), patch.object(legacy,'host_check'), patch.object(legacy,'GitLedger',Ledger), patch.object(legacy,'http',http), patch.object(w,'load_directive',return_value=directive):
            w.run(self.root)
            w.run(self.root)
        if context_verdict != 'SUFFICIENT':
            self.assertEqual(len(calls), 1)
            self.assertEqual(state['continuation']['status'], 'AWAITING_CHATGPT_CONTEXT_EXPANSION')
            return
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]['messages'], calls[1]['messages'])
        self.assertIn('Please find any defects or gaps or worthy upgrades.', calls[0]['messages'][0]['content'])
        self.assertIn('support_passages', calls[0]['messages'][0]['content'])
        self.assertEqual(state['attempts'][-1]['review_profile']['name'], 'COMPLEX')
        self.assertEqual(state['attempts'][-1]['spending']['daily_ceiling_usd'], '2')
        self.assertEqual(calls[0]['max_tokens'],16000)

    def test_context_expansion_cannot_reset_fifteen_call_task_budget(self):
        packet = self.packet()
        task_key = p.sha256_value({'target': self.target['target_id'], 'source_root': packet['source_root_sha256'], 'target_source': self.trace['source_sha256']})
        state = {'scope': 'PUBLIC_MATRIX_REVIEW_ONLY', 'paused': False, 'cycles': {},
                 'attempts': [{'inference_reserved': True, 'task_key': task_key, 'status': 'REVIEW_RECORDED'} for _ in range(15)]}
        class Ledger:
            def __init__(self, token): self.value = state
            def save(self, value): pass
        directive = {'schema': p.DIRECTIVE_SCHEMA, 'protocol': p.PROTOCOL_ID, 'public_only': True,
                     'target_id': self.target['target_id'], 'phase': 'BLIND', 'same_neutral_query_for_all_reviewers': True,
                     'source_packet_sha256': packet['packet_sha256'], 'reviewer_families': [r['family'] for r in self.policy['routine_reviewers']],
                     'private_baseline_commitment': {'schema': p.BASELINE_SCHEMA, 'baseline_sha256': 'd'*64,
                        'neutral_query_sha256': p.sha256_text(p.neutral_query(self.target)),
                        'source_packet_sha256': packet['packet_sha256'], 'created_before_openrouter_calls': True}}
        self.bind_directive(directive)
        with patch.dict(w.os.environ, {'OPENROUTER_API_KEY':'fixture','GH_REVIEW_TOKEN':'fixture'}), patch.object(legacy,'host_check'), patch.object(legacy,'GitLedger',Ledger), patch.object(legacy,'http') as http, patch.object(w,'load_directive',return_value=directive):
            with self.assertRaisesRegex(ValueError, 'cannot reset'):
                w.run(self.root)
            http.assert_not_called()

    def test_daily_exhaustion_persists_deferred_status(self):
        state = {}
        class Ledger:
            def __init__(self, token): self.value = state
            def save(self, value): pass
        with patch.dict(w.os.environ, {'GH_REVIEW_TOKEN':'fixture'}), patch.object(w, 'run', side_effect=legacy.DailyBudget('daily reservation exhausted')), patch.object(legacy,'host_check'), patch.object(legacy,'GitLedger',Ledger):
            with self.assertRaises(SystemExit):
                w.execute(self.root)
        self.assertEqual(state['continuation']['status'], 'DEFERRED_DAILY')
        self.assertGreater(state['continuation']['resume_after'], state['continuation']['updated'])

    def test_unrelated_model_suffix_is_not_identity_evidence(self):
        self.assertFalse(w._model_identity_matches('vendor/model', 'vendor/model-other'))
        self.assertTrue(w._model_identity_matches('vendor/model', 'vendor/model-date', {'id':'vendor/model','canonical_slug':'vendor/model-date'}))


if __name__ == '__main__':
    unittest.main()
