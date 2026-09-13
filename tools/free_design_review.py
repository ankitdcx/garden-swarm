#!/usr/bin/env python3
"""One bounded free-model review of a rotating Garden canonical-source chunk."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from urllib import request

from tools._free_review_common import parse_handoff_or_receipt

CHAT = "https://openrouter.ai/api/v1/chat/completions"
FILES = [
    "Garden_User_v15.5_FULL_2026-09-12.txt",
    "Garden_System_v15.5_FULL_2026-09-12.txt",
    "Garden_Technical_v15.5_FULL_2026-09-12.txt",
    "Garden_Annexure_v15.5_FULL_2026-09-12.txt",
    "Garden_Theories_v15.5_FULL_2026-09-12.txt",
]


def chunks(text: str, size: int = 14000) -> list[str]:
    out, cur, n = [], [], 0
    for p in text.split("\n\n"):
        add = len(p) + 2
        if cur and n + add > size:
            out.append("\n\n".join(cur)); cur, n = [], 0
        if len(p) > size:
            if cur:
                out.append("\n\n".join(cur)); cur, n = [], 0
            out.extend(p[i:i+size] for i in range(0, len(p), size)); continue
        cur.append(p); n += add
    if cur:
        out.append("\n\n".join(cur))
    return out or [""]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selection", default="agents/runtime/free-selection.json")
    p.add_argument("--output", default="agents/outbox/hourly/design-review.json")
    p.add_argument("--repo-root", default=".")
    args = p.parse_args()
    root = Path(args.repo_root).resolve()
    sel = json.loads((root / args.selection).read_text())
    model = sel["selected"][0]
    model_id = model["model"]
    if not model_id.endswith(":free"):
        raise SystemExit(f"paid route refused: {model_id}")
    slot = int(sel["hour_slot"])
    items = []
    for filename in FILES:
        raw = (root / filename).read_bytes()
        text = raw.decode("utf-8")
        parts = chunks(text)
        for i, part in enumerate(parts, 1):
            items.append((filename, hashlib.sha256(raw).hexdigest(), i, len(parts), part))
    filename, file_sha, index, total, source = items[slot % len(items)]
    task_id = f"DESIGN:{filename}:chunk-{index:03d}:{slot}"
    trace = [{"source":filename,"query_or_scope":f"chunk {index}/{total}; sha256={file_sha}","coverage":"BOUNDED"}]
    prompt = f"""You are an independent Garden reviewer. Posture: {model['role']} ({model['family']}).
Try to falsify or strengthen this bounded canonical source. Do not claim a mechanism is absent from Garden because it is absent from this chunk; use NEEDS_CROSS_REFERENCE. Distinguish source-design defect, implementation gap, missing evidence, optional enhancement, and coverage limitation. Return one JSON object only using GardenAgentHandoff/v1 with fields: schema, agent, agent_family, role, task_id, status, claim, evidence_or_failure, severity, affected_invariant, proposed_fix, test, uncertainty, what_would_overturn, search_trace. status is NO_CHANGE|PROPOSED|BLOCKER|NEEDS_CROSS_REFERENCE. search_trace is mandatory and may only cite this supplied chunk.
Task: {task_id}
Trace: {json.dumps(trace)}
--- BEGIN CANONICAL CHUNK ---
{source}
--- END CANONICAL CHUNK ---"""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY required")
    payload = {"model":model_id,"messages":[{"role":"user","content":prompt}],"temperature":0.15,"max_tokens":2800,"provider":{"allow_fallbacks":True}}
    req = request.Request(CHAT, method="POST", data=json.dumps(payload).encode(), headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://github.com/ankitdcx/garden-swarm","X-Title":"Garden Free Review Bus"})
    with request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode())
    usage = data.get("usage") or {}
    if usage.get("cost") not in (None, 0, 0.0):
        raise SystemExit(f"non-zero cost refused: {usage.get('cost')}")
    raw = data["choices"][0]["message"].get("content", "")
    handoff, output_status = parse_handoff_or_receipt(raw, trace=trace, model_id=model_id, family=model["family"], role=model["role"], task_id=task_id)
    receipt = {"schema":"GardenFreeDesignReviewReceipt/v1","model":model,"source_file":filename,"source_sha256":file_sha,"chunk_index":index,"chunk_count":total,"usage":usage,"output_status":output_status,"handoff":handoff,"admission_status":"PROPOSALS_ONLY_NEEDS_WHOLE_SOURCE_CROSS_REFERENCE"}
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps({"model":model_id,"source":filename,"chunk":f"{index}/{total}","cost":usage.get("cost"),"status":handoff.get("status"),"output_status":output_status}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
