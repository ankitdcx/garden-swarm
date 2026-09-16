from __future__ import annotations

import json
from pathlib import Path
from typing import Any

POLICY_PATH = Path("agents/provider-exclusion-policy.json")


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "GardenProviderExclusionPolicy/v1":
        raise RuntimeError("unsupported Garden provider exclusion policy schema")
    if payload.get("enforcement", {}).get("fail_closed") is not True:
        raise RuntimeError("Garden provider exclusion policy must remain fail-closed")
    return payload


def _tokens(policy: dict[str, Any]) -> tuple[set[str], list[str], set[str]]:
    families: set[str] = set()
    model_markers: list[str] = []
    providers: set[str] = set()
    for row in policy.get("excluded") or []:
        families.update(str(x).strip().lower() for x in row.get("family_aliases") or [] if str(x).strip())
        model_markers.extend(str(x).strip().lower() for x in row.get("model_markers") or [] if str(x).strip())
        providers.update(str(x).strip().lower() for x in row.get("provider_slugs") or [] if str(x).strip())
    return families, model_markers, providers


def exclusion_reason(*, model_id: str, family: str | None = None, policy: dict[str, Any] | None = None) -> str | None:
    policy = policy or load_policy()
    families, markers, _ = _tokens(policy)
    normalized_model = str(model_id).strip().lower()
    normalized_family = str(family or "").strip().lower()
    if normalized_family and any(alias == normalized_family or alias in normalized_family for alias in families):
        return f"excluded family alias: {family}"
    if any(marker in normalized_model for marker in markers):
        return f"excluded model origin marker: {model_id}"
    return None


def require_allowed_model(*, model_id: str, family: str | None = None, policy: dict[str, Any] | None = None) -> None:
    reason = exclusion_reason(model_id=model_id, family=family, policy=policy)
    if reason:
        raise RuntimeError(f"GARDEN_PROVIDER_EXCLUDED: {reason}")


def model_allowed(model: dict[str, Any], policy: dict[str, Any] | None = None) -> bool:
    model_id = str(model.get("id") or model.get("model") or "")
    family = model.get("family")
    return exclusion_reason(model_id=model_id, family=None if family is None else str(family), policy=policy) is None


def excluded_provider_slugs(policy: dict[str, Any] | None = None) -> list[str]:
    policy = policy or load_policy()
    _, _, providers = _tokens(policy)
    return sorted(providers)


def openrouter_provider_policy(base: dict[str, Any] | None = None, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(base or {})
    existing = {str(x).strip().lower() for x in out.get("ignore") or [] if str(x).strip()}
    existing.update(excluded_provider_slugs(policy))
    out["ignore"] = sorted(existing)
    return out
