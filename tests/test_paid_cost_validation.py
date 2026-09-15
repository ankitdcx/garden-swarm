import json
import os
import unittest
from unittest.mock import patch

from tools import run_paid_matrix_review as paid


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode('utf-8')


class PaidCostValidationTests(unittest.TestCase):
    def test_invalid_daily_usage_cannot_be_verified(self):
        for value in (-1, 'NaN', 'Infinity', '-Infinity', True, None, 'invalid'):
            with self.subTest(value=value), patch.object(paid.request, 'urlopen', return_value=Response({'data': {'usage_daily': value}})):
                usage, receipt = paid._key_usage_daily('test-key')
                self.assertIsNone(usage)
                self.assertEqual(receipt['status'], 'DAILY_USAGE_UNVERIFIED')

    def test_invalid_daily_usage_prevents_a_billable_post(self):
        selection = self.selection()
        selection['daily_openrouter_cost_ceiling_usd'] = 1.0
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), patch.object(paid.request, 'urlopen', return_value=Response({'data': {'usage_daily': 'NaN'}})) as call:
            raw, receipt = paid._call(model={'model': 'example/model', 'family': 'example'}, prompt='bounded', selection=selection)
        self.assertIsNone(raw)
        self.assertEqual(receipt['status'], 'DAILY_USAGE_UNVERIFIED')
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.args[0].get_method(), 'GET')

    @staticmethod
    def selection():
        return {'approved_families': ['example'], 'max_prompt_characters': 100,
                'max_output_tokens': 10, 'routine_model_call_cost_ceiling_usd': 0.01,
                'provider_policy': {'max_price_usd_per_million_tokens': {'prompt': 0.25, 'completion': 0.75}}}

    def test_invalid_provider_cost_never_qualifies_a_finding(self):
        for value in (-0.5, 'NaN', 'Infinity', True, {}, 'invalid'):
            payload = {'usage': {'cost': value}, 'choices': [{'message': {'content': '{"ok": true}'}}]}
            with self.subTest(value=value), patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), patch.object(paid.request, 'urlopen', return_value=Response(payload)):
                raw, receipt = paid._call(model={'model': 'example/model', 'family': 'example'}, prompt='bounded', selection=self.selection())
            self.assertIsNone(raw)
            self.assertIsNone(receipt['cost'])
            self.assertEqual(receipt['status'], 'COST_UNVERIFIED')
