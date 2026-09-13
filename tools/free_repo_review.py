#!/usr/bin/env python3
"""One bounded free-model review of a rotating public executable Garden package."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from urllib import request

from tools._free_review_common import parse_handoff_or_receipt

CHAT = "https://openrouter.ai/api/v1/chat/completions"
PACKAGES = [
    ("authority-gate", ["prototype/actiongate.py", "prototype/authority.py", "prototype/tests/test_actiongate.py", "tests/adversarial/test_known_attacks.py"]),
    ("design-epoch", ["prototype/design_epoch.py", "prototype/tests/test_design_epoch.py", "tests/adversarial/test_known_attacks.py"]),
    ("receipts", ["prototype/tokens.py", "prototype/tests/test_tokens.py", "ATTACK_SURFACE.md"]),
    ("discovery-mcp", ["server/app.py", "server/mcp_service.py", "server/tests/test_mcp.py", "DISCOVERY.json", "SKILLS.json"]),
    ("swarm", ["swarm/orchestrator.py", "swarm/synthesize.py", "swarm/roles-free.json", "swarm/tests/test_synthesize.py"]),
    ("evaluation-release", ["AGENTS.md", "ATTACK_SURFACE.md", "EVALUATION_LOG.md", "EVALUATE_IN_10_MINUTES.md", "scripts/verify_public_release.py"]),
]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selection", default="agents/runtime/free-selection.json")
    p.add_argument("--output", default="agents/outbox/hourly/repo-review.json")
    p.add_argument("--repo-root", default=".")
    args = p.parse_args()
    root = Path(args.repo_root).resolve()
    sel = json.loads((root / args.selection).read_text())
    model = sel["selected"][1]
    model_id = model["model"]
    if not model_id.endswith(":free"):
        raise SystemExit(f"paid route refused: {model_id}")
    slot = int(sel["hour_slot"])
    package, files = PACKAGES[slot % len(PACKAGES)]
    sections, trace = [], []
    for rel in files:
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        coverage = "FULL"
        if len(text) > 14000:
            text, coverage = text[:14000] + "\n...[bounded]", "PARTIAL"
        sections.append(f"\n--- {rel} ---\n{text}")
        trace.append({"source": rel, "query_or_scope": "supplied file content", "coverage": coverage})
    source = "\n".join(sections)
    task_id = f"REPO:{package}:{slot}"
    prompt = f"""You are an independent Garden reviewer. Posture: {model['role']} ({model['family']}).
Try to falsify this bounded executable package before suggesting improvements. Separate implementation defect, design defect, missing evidence, and coverage limit. Do not claim anything about files not supplied. Return one JSON object only using GardenAgentHandoff/v1 with fields: schema, agent, agent_family, role, task_id, status, claim, evidence_or_failure, severity, affected_invariant, proposed_fix, test, uncertainty, what_would_overturn, search_trace. status is NO_CHANGE|PROPOSED|BLOCKER|NEEDS_CROSS_REFERENCE. search_trace is mandatory and may only cite supplied files.
Task: {task_id}
Precomputed supplied trace: {json.dumps(trace)}
--- BEGIN PACKAGE ---
{source}
--- END PACKAGE ---"""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY required")
    payload = {"model": model_id, "messages": [{"role":"user","content":prompt}], "temperature":0.15, "max_tokens":2800, "provider":{"allow_fallbacks":True}}
    req = request.Request(CHAT, method="POST", data=json.dumps(payload).encode(), headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://github.com/ankitdcx/garden-swarm","X-Title":"Garden Free Review Bus"})
    with request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode())
    usage = data.get("usage") or {}
    if usage.get("cost") not in (None, 0, 0.0):
        raise SystemExit(f"non-zero cost refused: {usage.get('cost')}")
    raw = data["choices"][0]["message"].get("content", "")
    handoff, output_status = parse_handoff_or_receipt(raw, trace=trace, model_id=model_id, family=model["family"], role=model["role"], task_id=task_id)
    receipt = {"schema":"GardenFreeRepoReviewReceipt/v1", "model":model, "package":package, "source_sha256":digest(source), "usage":usage, "output_status":output_status, "handoff":handoff, "admission_status":"PROPOSALS_ONLY"}
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps({"model":model_id,"package":package,"cost":usage.get("cost"),"status":handoff.get("status"),"output_status":output_status}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
