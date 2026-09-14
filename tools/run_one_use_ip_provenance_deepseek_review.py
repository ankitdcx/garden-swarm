#!/usr/bin/env python3
"""One-use public-only DeepSeek review of Garden IP provenance wording.

Proposal evidence only. This script never admits semantic changes and refuses
non-public inputs by construction: it reads only the public notice + LICENSE.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from tools.run_paid_matrix_review import _call

NOTICE = Path("PATENT_AND_USE_NOTICE.md")
LICENSE = Path("LICENSE")
SELECTION = Path("agents/runtime/paid-selection.json")
OUT = Path("ip-provenance-deepseek-review.json")


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY unavailable")
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    deepseek = next((row for row in selection.get("selected", []) if row.get("family") == "deepseek"), None)
    if deepseek is None:
        raise SystemExit("approved DeepSeek paid reviewer unavailable")

    notice = NOTICE.read_text(encoding="utf-8")
    license_text = LICENSE.read_text(encoding="utf-8")
    prompt = f"""You are an independent adversarial reviewer of PUBLIC Garden repository material only.
Do not assume patentability, ownership, priority, validity, infringement, or enforceability merely because the text says so.
Do not invent legal facts. Review the exact public text below for:
1. unsupported patent/grant/priority claims;
2. accidental disclosure of NEW enabling technical detail beyond an already-public provenance summary;
3. provenance/date statements that are overconfident or should be qualified;
4. contradictions with the repository licence;
5. wording that could falsely imply legal certification;
6. any material issue that should block publishing this public notice.

This is a public-document consistency/confidentiality audit, not legal advice.
Return ONLY one JSON object with exactly these top-level keys:
verdict (PASS or BLOCK), blocking_findings (array), nonblocking_findings (array), confidentiality_risk (LOW/MEDIUM/HIGH), patent_status_overclaim (boolean), summary (string).

PATENT_AND_USE_NOTICE.md:\n{notice}\n\nLICENSE:\n{license_text}\n"""

    raw, attempt = _call(model=deepseek, prompt=prompt, selection=selection)
    if raw is None:
        raise SystemExit("DeepSeek review did not return usable JSON: " + json.dumps(attempt, sort_keys=True))
    required = {
        "verdict",
        "blocking_findings",
        "nonblocking_findings",
        "confidentiality_risk",
        "patent_status_overclaim",
        "summary",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise SystemExit(f"DeepSeek review missing required keys: {missing}")
    if raw["verdict"] not in {"PASS", "BLOCK"}:
        raise SystemExit("DeepSeek verdict must be PASS or BLOCK")
    if raw["confidentiality_risk"] not in {"LOW", "MEDIUM", "HIGH"}:
        raise SystemExit("invalid confidentiality_risk")
    if not isinstance(raw["blocking_findings"], list) or not isinstance(raw["nonblocking_findings"], list):
        raise SystemExit("DeepSeek finding fields must be arrays")
    if not isinstance(raw["patent_status_overclaim"], bool):
        raise SystemExit("patent_status_overclaim must be boolean")

    receipt = {
        "schema": "GardenPublicIPProvenanceDeepSeekReview/v1",
        "model": attempt.get("model"),
        "family": attempt.get("family"),
        "provider_status": attempt.get("status"),
        "cost_usd": attempt.get("cost"),
        "provider_policy": {"data_collection": selection["provider_policy"].get("data_collection")},
        "commit": os.environ.get("GITHUB_SHA"),
        "review": raw,
        "semantic_delta_admitted": False,
        "legal_opinion": False,
        "private_material_reviewed": False,
    }
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    if raw["verdict"] == "BLOCK" or raw["blocking_findings"]:
        raise SystemExit("DeepSeek public IP/provenance review returned blocking findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
