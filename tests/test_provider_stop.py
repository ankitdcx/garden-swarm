import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import matrix_design_review as free
from tools import run_paid_matrix_review as paid
from tools import run_ip_origin_multi_agent_review as ip

ROOT = Path(__file__).resolve().parents[1]


class ProviderStopTests(unittest.TestCase):
    def test_free_batch_stops_after_first_429_and_preserves_partial_bundle(self):
        selected=[{'family':f,'model':f+'/m:free'} for f in ['a','b','c']]
        matrix,target=free.load_matrix(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);selection=root/'selection.json';selection.write_text(json.dumps({'selected':selected}))
            with patch.object(free,'SELECTION',selection), patch.object(free,'OUT_DIR',root/'out'), patch.object(free,'BUNDLE',root/'bundle.json'), patch.object(free,'load_matrix',return_value=(matrix,target)), patch.object(free,'extract_target',return_value=('public source',{})), patch.object(free,'independent_prompt',return_value='prompt'), patch.object(free,'call_openrouter',return_value=(None,{'status':'HTTP_429','cost':None})) as call:
                free.main()
                self.assertEqual(call.call_count,1)
                result=json.loads((root/'bundle.json').read_text())
                self.assertFalse(result['semantic_delta_admitted'])
                self.assertNotEqual(result['status'],'REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR')

    def test_paid_batch_stops_after_first_provider_failure(self):
        selection={'schema':'GardenPaidModelSelection/v2','design_epoch':'v15.5','selected':[{'family':f,'model':f+'/m'} for f in ['a','b']], 'approved_families':['a','b'],'routine_hourly_cost_ceiling_usd':0.45,'routine_model_call_cost_ceiling_usd':0.15,'daily_openrouter_cost_ceiling_usd':1}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'selection.json';p.write_text(json.dumps(selection))
            with patch.object(paid,'SELECTION',p), patch.object(paid,'OUT_DIR',root/'out'), patch.object(paid,'BUNDLE',root/'bundle.json'), patch.object(paid.review,'load_matrix',return_value=({'design_epoch':'v15.5','canonical_source_root_sha256':'s'},{'target_id':'t','public_only':True})), patch.object(paid.review,'extract_target',return_value=('source',{})), patch.object(paid.review,'independent_prompt',return_value='prompt'), patch.object(paid,'_call',return_value=(None,{'status':'HTTP_429','cost':None})) as call:
                paid.main()
                self.assertEqual(call.call_count,1)
                self.assertEqual(json.loads((root/'bundle.json').read_text())['status'],'PARTIAL_PAID_REVIEW_PROPOSALS_ONLY')

    def test_origin_backfill_stops_entire_multibatch_sweep(self):
        families=['deepseek','qwen','glm']
        selection={'selected':[{'family':f,'model':f+'/m'} for f in families],'approved_families':families,'provider_policy':{'data_collection':'deny'},'routine_model_call_cost_ceiling_usd':0.15}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'selection.json';p.write_text(json.dumps(selection))
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'mock'}), patch.object(ip,'SELECTION',p), patch.object(ip,'OUT',root/'receipt.json'), patch.object(ip,'load_records',return_value=([{'id':str(i)} for i in range(50)],None)), patch.object(ip,'_call',return_value=(None,{'status':'HTTP_429','cost':None})) as call:
                with self.assertRaises(SystemExit):
                    ip.main()
                self.assertEqual(call.call_count,1)
                receipt=json.loads((root/'receipt.json').read_text())
                self.assertFalse(receipt['complete'])
                self.assertEqual(len(receipt['calls']),1)
