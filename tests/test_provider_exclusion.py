from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.free_model_rotation import choose
from tools.provider_exclusion import (
    excluded_provider_slugs,
    load_policy,
    openrouter_provider_policy,
    require_allowed_model,
)

ROOT = Path(__file__).resolve().parents[1]


class ProviderExclusionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy(ROOT / "agents/provider-exclusion-policy.json")

    def test_excluded_model_origins_fail_closed(self) -> None:
        blocked = [
            ("anthropic/claude-example", "anthropic"),
            ("third-party/claude-derived-example", "other"),
            ("nvidia/nemotron-example", "nvidia"),
            ("third-party/nemotron-example", "other"),
        ]
        for model_id, family in blocked:
            with self.subTest(model=model_id):
                with self.assertRaisesRegex(RuntimeError, "GARDEN_PROVIDER_EXCLUDED"):
                    require_allowed_model(model_id=model_id, family=family, policy=self.policy)
        require_allowed_model(model_id="deepseek/example", family="deepseek", policy=self.policy)

    def test_openrouter_provider_routes_ignore_excluded_endpoints(self) -> None:
        self.assertEqual(excluded_provider_slugs(self.policy), ["anthropic", "nvidia"])
        routed = openrouter_provider_policy({"allow_fallbacks": True, "ignore": ["other-provider"]}, self.policy)
        self.assertEqual(routed["ignore"], ["anthropic", "nvidia", "other-provider"])

    def test_free_selector_skips_excluded_model_origins(self) -> None:
        models = [
            {"id": "nvidia/nemotron-example:free", "context_length": 999999},
            {"id": "deepseek/a:free", "context_length": 10},
            {"id": "qwen/a:free", "context_length": 20},
            {"id": "mistralai/a:free", "context_length": 30},
        ]
        picked = choose(models, slot=0, count=3)
        self.assertEqual(len(picked), 3)
        self.assertFalse(any("nvidia" in row["model"].lower() or "nemotron" in row["model"].lower() for row in picked))

    def test_active_role_sets_do_not_assign_excluded_models(self) -> None:
        for rel in ("swarm/roles.json", "swarm/roles-free.json"):
            payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            for row in payload["roles"]:
                require_allowed_model(model_id=str(row["model"]), family=str(row["id"]), policy=self.policy)


if __name__ == "__main__":
    unittest.main()
