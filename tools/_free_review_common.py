from __future__ import annotations

import json
import re
from typing import Any


def parse_handoff_or_receipt(text: str, *, trace: list[dict[str, Any]], model_id: str, family: str, role: str, task_id: str) -> tuple[dict[str, Any], str]:
    """Parse a model handoff without allowing formatting failure to crash the bus.

    Returns (handoff, output_status). Invalid/empty outputs remain proposal-only
    evidence and are never promoted to Garden findings.
    """
    raw = (text or "").strip()
    cleaned = raw
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    value = None
    error = None
    if cleaned:
        try:
            value = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            match = re.search(r"\{.*\}", cleaned, re.S)
            if match:
                try:
                    value = json.loads(match.group(0))
                except json.JSONDecodeError as nested:
                    error = f"INVALID_JSON:{nested.msg}"
            else:
                error = f"INVALID_JSON:{exc.msg}"
    else:
        error = "EMPTY_OUTPUT"

    if not isinstance(value, dict) or not value.get("search_trace"):
        reason = error or "MISSING_SEARCH_TRACE_OR_OBJECT"
        handoff = {
            "schema": "GardenAgentHandoff/v1",
            "agent": model_id,
            "agent_family": family,
            "role": role,
            "task_id": task_id,
            "status": "INVALID_OUTPUT",
            "claim": "No admissible reviewer finding was produced.",
            "evidence_or_failure": reason,
            "severity": "INFO",
            "affected_invariant": "review-output schema discipline",
            "proposed_fix": "None automatically; rotate/retry another free model on a later scheduled run.",
            "test": "Reviewer must return one JSON object with a non-empty search_trace.",
            "uncertainty": "The model may have reasoned internally but failed to emit a usable final answer.",
            "what_would_overturn": "A later valid structured handoff for the same task/source.",
            "search_trace": trace,
            "raw_output_excerpt": raw[:2000],
        }
        return handoff, "INVALID_OUTPUT"

    value.update({
        "schema": "GardenAgentHandoff/v1",
        "agent": model_id,
        "agent_family": family,
        "role": role,
        "task_id": task_id,
    })
    return value, "USABLE"
