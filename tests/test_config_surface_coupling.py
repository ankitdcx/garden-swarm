import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import select_paid_matrix_reviewers as routine_selector
from tools.select_ip_origin_reviewers import build_selection as build_ip_selection


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "agents/openrouter-paid-review-policy.json"
CONTRACTS = ROOT / "agents/config-surface-contracts.json"


def current_shape(policy):
    contracts = json.loads(CONTRACTS.read_text())
    surface = contracts['surfaces'][0]
    shape = {}
    for field in surface['watched_fields']:
        value = policy
        parts = field.split('.')
        for part in parts:
            value = value[part]
        out = shape
        for part in parts[:-1]:
            out = out.setdefault(part, {})
        out[parts[-1]] = value
    return shape


def shape_hash(policy):
    encoded = json.dumps(current_shape(policy), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ConfigSurfaceCouplingTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
        self.surface = next(
            row for row in self.contracts["surfaces"]
            if row["surface_id"] == "OPENROUTER_PAID_REVIEW_SHAPE"
        )

    def test_manifest_and_every_consumer_acknowledge_current_shape(self):
        self.assertEqual(self.contracts["schema"], "GardenConfigSurfaceContracts/v1")
        observed = shape_hash(self.policy)
        self.assertEqual(self.surface["accepted_shape_sha256"], observed)
        self.assertGreaterEqual(len(self.surface["consumers"]), 8)
        for consumer in self.surface["consumers"]:
            with self.subTest(consumer=consumer["path"]):
                self.assertEqual(consumer["accepted_shape_sha256"], observed)
                self.assertTrue((ROOT / consumer["path"]).is_file())
                self.assertTrue(consumer["binding"])

    def test_free_and_specialist_mutations_invalidate_fingerprint(self):
        import copy
        watched = set(self.surface['watched_fields'])
        for section in ('free_swarm', 'specialist_free_sweep', 'execution_limits'):
            for field in self.policy[section]:
                self.assertIn(section + '.' + field, watched)
                mutated = copy.deepcopy(self.policy)
                mutated[section][field] = 'INVALID_CHANGED_VALUE'
                self.assertNotEqual(shape_hash(mutated), self.surface['accepted_shape_sha256'])

    def test_routine_and_ip_selectors_follow_authoritative_policy_shape(self):
        expected = [row["family"] for row in self.policy["routine_reviewers"]]
        self.assertEqual(len(expected), len(set(expected)))
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            routine_selector, "OUTPUT", Path(tmp) / "selection.json"
        ):
            self.assertEqual(routine_selector.main(), 0)
            routine = json.loads((Path(tmp) / "selection.json").read_text(encoding="utf-8"))
        self.assertEqual([row["family"] for row in routine["selected"]], expected)
        self.assertEqual(routine["approved_families"], expected)

        ip = build_ip_selection(self.policy)
        self.assertEqual([row["family"] for row in ip["selected"]], expected)
        self.assertEqual(ip["approved_families"], expected)
        self.assertTrue(set(ip["anchor_families"]).issubset(set(expected)))

    def test_reviewer_cardinality_and_call_cap_fit_hourly_budget(self):
        count = len(self.policy["routine_reviewers"])
        per_call = float(self.policy["routine_model_call_cost_ceiling_usd"])
        hourly = float(self.policy["routine_hourly_cost_ceiling_usd"])
        self.assertLessEqual(count * per_call, hourly)

    def test_runners_bind_to_selection_instead_of_static_full_family_list(self):
        routine = (ROOT / "tools/run_paid_matrix_review.py").read_text(encoding="utf-8")
        ip = (ROOT / "tools/run_ip_origin_multi_agent_review.py").read_text(encoding="utf-8")
        self.assertIn("approved_families", routine)
        self.assertIn("approved_families", ip)
        self.assertIn("selection.get", routine)
        self.assertIn("selection.get", ip)


if __name__ == "__main__":
    unittest.main()
