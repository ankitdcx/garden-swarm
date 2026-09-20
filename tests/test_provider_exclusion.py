from __future__ import annotations

import json
import unittest
from pathlib import Path

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

    def test_2026_09_20_human_override_reauthorizes_claude_nemotron_and_mistral_review(self) -> None:
        for model_id, family in [
            ("anthropic/claude-example", "anthropic"),
            ("third-party/claude-derived-example", "other"),
            ("nvidia/nemotron-example", "nvidia"),
            ("mistralai/mistral-example", "mistral"),
            ("deepseek/example", "deepseek"),
        ]:
            require_allowed_model(model_id=model_id, family=family, policy=self.policy)

    def test_openrouter_provider_routes_have_no_current_exclusion_endpoints(self) -> None:
        self.assertEqual(excluded_provider_slugs(self.policy), [])
        routed = openrouter_provider_policy({"allow_fallbacks": True, "ignore": ["other-provider"]}, self.policy)
        self.assertEqual(routed["ignore"], ["other-provider"])

    def test_active_role_sets_do_not_assign_currently_excluded_models(self) -> None:
        for rel in ("swarm/roles.json", "swarm/roles-free.json"):
            payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            for row in payload["roles"]:
                require_allowed_model(model_id=str(row["model"]), family=str(row["id"]), policy=self.policy)


if __name__ == "__main__":
    unittest.main()
