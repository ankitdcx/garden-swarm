#!/usr/bin/env python3
"""Build a compact, provenance-preserving material-context packet for Garden review."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

POLICY = Path("agents/event-driven-context-policy.json")
DEFAULT_INPUT = Path("agents/runtime/normalized-observations.json")
DEFAULT_OUTPUT = Path("agents/runtime/material-context.json")


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_policy(path: Path = POLICY) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema") != "GardenEventDrivenContextPolicy/v2":
        raise ValueError("unsupported event-driven context policy schema")
    if policy.get("public_only") is not True:
        raise ValueError("public adapter policy must remain public-only")
    return policy


def _validate_observation(row: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    required = policy["normalization"]["required_fields"]
    missing = [key for key in required if key not in row]
    if missing:
        raise ValueError(f"normalized observation missing fields: {missing}")
    if row.get("public_only") is not True:
        raise ValueError("non-public observation refused by public context adapter")
    if not isinstance(row.get("changed_fields"), list):
        raise ValueError("changed_fields must be a list")
    if not isinstance(row.get("source_refs"), list) or not row["source_refs"]:
        raise ValueError("source_refs must be a non-empty list")
    if not isinstance(row.get("evidence_refs"), list):
        raise ValueError("evidence_refs must be a list")
    observed = row.get("observed_at_unix")
    if isinstance(observed, bool) or not isinstance(observed, (int, float)) or observed < 0:
        raise ValueError("observed_at_unix must be nonnegative")
    clean = dict(row)
    clean.setdefault("contradiction", False)
    clean.setdefault("expires_at_unix", None)
    clean.setdefault("parent_observation_ids", [])
    clean.setdefault("overturns_observation_ids", [])
    clean.setdefault("producer", "UNKNOWN")
    return clean


def _is_stale(row: dict[str, Any], now: float) -> bool:
    expiry = row.get("expires_at_unix")
    if expiry is None:
        return False
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or expiry < 0:
        raise ValueError("expires_at_unix must be null or nonnegative")
    return float(expiry) < now


def _material_reasons(row: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    cfg = policy["materiality"]
    reasons: list[str] = []
    risk_order = list(cfg["risk_order"])
    risk = str(row["risk"]).upper()
    if risk not in risk_order:
        raise ValueError(f"unknown risk {risk}")
    threshold = str(cfg["risk_at_or_above"]).upper()
    if risk_order.index(risk) >= risk_order.index(threshold):
        reasons.append(f"RISK_{risk}")
    kind = str(row["event_kind"]).upper()
    if kind in {str(x).upper() for x in cfg["trigger_event_kinds"]}:
        reasons.append(f"EVENT_{kind}")
    uncertainty = str(row["uncertainty"]).upper()
    if uncertainty in {str(x).upper() for x in cfg["trigger_uncertainty"]}:
        reasons.append(f"UNCERTAINTY_{uncertainty}")
    if cfg.get("contradiction_always_material") and row.get("contradiction") is True:
        reasons.append("CONTRADICTION")
    return reasons


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    keep = [
        "observation_id", "observed_at_unix", "subject", "event_kind", "fingerprint",
        "changed_fields", "risk", "uncertainty", "source_refs", "evidence_refs", "summary",
        "contradiction", "parent_observation_ids", "overturns_observation_ids", "producer",
    ]
    return {key: row.get(key) for key in keep if key in row}


def build_packet(observations: list[dict[str, Any]], policy: dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else float(now)
    validated = [_validate_observation(row, policy) for row in observations]

    # Preserve only the newest exact semantic replay. Different fingerprints remain
    # separate so relevant contradictions cannot disappear behind subject-level dedupe.
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for row in sorted(validated, key=lambda r: (float(r["observed_at_unix"]), str(r["observation_id"]))):
        key = (str(row["subject"]), str(row["fingerprint"]))
        old = dedup.get(key)
        if old is not None:
            duplicate_ids.append(str(old["observation_id"]))
        dedup[key] = row

    active: list[dict[str, Any]] = []
    stale_ids: list[str] = []
    reasons: dict[str, list[str]] = {}
    for row in dedup.values():
        if _is_stale(row, now):
            stale_ids.append(str(row["observation_id"]))
            continue
        active.append(row)
        why = _material_reasons(row, policy)
        if why:
            reasons[str(row["observation_id"])] = why

    active.sort(key=lambda r: (str(r["subject"]), float(r["observed_at_unix"]), str(r["observation_id"])))
    compact = [_compact(row) for row in active]
    material = bool(reasons)
    omitted = [
        *({"observation_id": oid, "reason": "DUPLICATE_REPLAY_SUPERSEDED"} for oid in duplicate_ids),
        *({"observation_id": oid, "reason": "STALE_REQUIRES_REVALIDATION"} for oid in stale_ids),
    ]
    payload = {
        "schema": policy["context_packet"]["schema"],
        "created_at_unix": now,
        "public_only": True,
        "material": material,
        "materiality_reasons": reasons,
        "observations": compact,
        "omitted_observations": omitted,
        "raw_observation_count": len(validated),
        "deduplicated_observation_count": len(dedup),
        "active_observation_count": len(active),
        "stale_observation_count": len(stale_ids),
        "frontier_handoff_eligible": material and bool(policy["frontier_handoff"]["enabled"]),
        "semantic_delta_admitted": False,
        "authority_granted": False,
        "compression_boundary": (
            "Derived routing/context view only. Source/evidence refs remain back-pointers; "
            "raw evidence remains owned by its source contract and omissions are explicit."
        ),
        "full_context_fallback_rule": policy["full_context_fallback"]["required_when"],
    }
    chars = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    payload["context_characters"] = chars
    if chars > int(policy["context_packet"]["max_prompt_characters"]):
        payload["frontier_handoff_eligible"] = False
        payload["packet_status"] = "MATERIAL_BUT_TOO_LARGE_REQUIRES_EXPLICIT_RECOMPACTION_OR_CONTEXT_EXPANSION"
    else:
        payload["packet_status"] = "MATERIAL" if material else "NOT_MATERIAL"
    payload["packet_sha256"] = _hash({k: v for k, v in payload.items() if k != "packet_sha256"})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--now", type=float)
    args = parser.parse_args()
    policy = load_policy()
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    observations = raw.get("observations") if isinstance(raw, dict) else raw
    if not isinstance(observations, list):
        raise SystemExit("input must be a JSON array or object with observations array")
    packet = build_packet(observations, policy, now=args.now)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "packet_status": packet["packet_status"],
        "material": packet["material"],
        "raw_observations": packet["raw_observation_count"],
        "active_observations": packet["active_observation_count"],
        "context_characters": packet["context_characters"],
        "frontier_handoff_eligible": packet["frontier_handoff_eligible"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
