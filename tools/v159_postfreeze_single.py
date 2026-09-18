#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, time
from urllib import request, error
from pathlib import Path

OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
REGISTRY = Path("agents/reviewer-slot-registry.json")
BASELINE = Path("review-inputs/v159-postfreeze/CHATGPT_BASELINE.txt")
OUT = Path("review-results/v159-postfreeze")
TIMEOUT = 240
KEY_INFO = "https://openrouter.ai/api/v1/key"
DAILY_CEILING = 10.0
PER_CALL_CEILING = 0.10


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_model(family: str) -> str:
    reg = json.loads(REGISTRY.read_text())
    matches = [s for s in reg.get("slots", []) if s.get("family") == family and s.get("state") == "ACTIVE"]
    if len(matches) != 1:
        raise RuntimeError(f"family {family} does not resolve to exactly one ACTIVE governed slot")
    return matches[0]["model"]


def build_prompt(packet: str, baseline: str, family: str, packet_sha: str) -> str:
    schema = {
        "verdict": "KEEP|CHANGE|MIXED|REJECT|EXPAND_REQUIRED",
        "summary": "...",
        "findings": [{
            "id": "F1",
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "candidate_semantic": "...",
            "disposition": "NEW|EXTENDS|REFINES|ALIAS|DUPLICATE|REJECT|DEFER|UNRESOLVED",
            "claim": "...",
            "existing_owner_or_overlap": "...",
            "minimal_repair": "...",
            "test": "...",
            "confidence": "HIGH|MEDIUM|LOW",
            "needs_more_context": False
        }],
        "retain": [], "reject_or_merge": [], "context_requests": []
    }
    return f'''BLIND INDEPENDENT GARDEN v15.9 POST-FREEZE DESIGN REVIEW.
Reviewer family: {family}
Packet SHA-256: {packet_sha}

You have NOT seen ChatGPT synthesis or peer answers. Do not infer consensus.
The baseline below is current-v15.9 comparator context; the candidate packet follows it.

REVIEW RULES
- Compare every proposed semantic against DO_NOTHING and existing owners.
- Prefer ALIAS/DUPLICATE/REFINES over ontology growth when current v15.9 already closes the need.
- Authority does not arise from capability, evidence, model agreement, reputation, access, technical possession, or successful outcome.
- UNKNOWN/STALE/CONFLICT/BLOCKED/INCOMPLETE/NEEDS_REVALIDATION are not PASS where hard resolution is required.
- Rights/privacy/consent/legitimate authority/safety/law/appeal/human agency remain hard applicable boundaries.
- Specification != proof != implementation != validation != certification.
- If material context is missing, set needs_more_context=true and request the exact anchor instead of guessing.
- Do not claim external research or executed tests.

Return concise JSON matching this shape:
{json.dumps(schema, ensure_ascii=False)}

--- CURRENT v15.9 BASELINE ---
{baseline}
--- END BASELINE ---

--- CANDIDATE PACKET ---
{packet}
--- END PACKET ---
'''


def call(model: str, text: str, key: str):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "temperature": 0.05,
        "max_tokens": 3500,
        "stream": False,
        "provider": {"allow_fallbacks": True, "data_collection": "deny", "sort": "price", "ignore": ["anthropic", "mistral", "nvidia"], "max_price": {"prompt": 0.25, "completion": 1.0}}
    }
    cmd = [
        "curl", "-sS", "--connect-timeout", "10", "--max-time", str(TIMEOUT),
        OPENROUTER, "-X", "POST",
        "-H", "Authorization: Bearer " + key,
        "-H", "Content-Type: application/json",
        "-H", "HTTP-Referer: https://github.com/ankitdcx/garden-swarm",
        "-H", "X-Title: Garden v15.9 Post-Freeze Review",
        "--data-binary", "@-",
        "-w", "\\n%{http_code}"
    ]
    p = subprocess.run(cmd, input=json.dumps(body, separators=(",", ":")), text=True,
                       capture_output=True, timeout=TIMEOUT + 15)
    raw = p.stdout
    if "\n" not in raw:
        return 0, None, f"NO_STATUS rc={p.returncode} stderr={p.stderr[-500:]}"
    payload, status_text = raw.rsplit("\n", 1)
    try:
        status = int(status_text.strip())
    except Exception:
        status = 0
    if p.returncode != 0:
        return status, None, f"CURL_{p.returncode}"
    try:
        data = json.loads(payload)
    except Exception:
        data = {"raw_payload": payload}
    if not 200 <= status < 300:
        return status, data, f"HTTP_{status}:" + json.dumps(data, ensure_ascii=False)[:1000]
    return status, data, None


def key_budget_status(key: str):
    req = request.Request(KEY_INFO, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as exc:
        return None, {"status": "UNVERIFIED", "detail": f"{type(exc).__name__}: {exc}"}
    payload = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else data
    try:
        usage = float(payload.get("usage_daily"))
        if not math.isfinite(usage) or usage < 0:
            raise ValueError("invalid usage")
    except Exception:
        return None, {"status": "UNVERIFIED", "raw_usage_daily": payload.get("usage_daily") if isinstance(payload, dict) else None}
    return usage, {"status": "VERIFIED", "usage_daily": usage, "limit": payload.get("limit"), "limit_remaining": payload.get("limit_remaining")}

def parse_content(data):
    choices = (data or {}).get("choices") or []
    if not choices:
        return None, ""
    msg = choices[0].get("message") or {}
    text = (msg.get("content") or "").strip()
    s = text
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
        if s.lower().startswith("json\n"):
            s = s[5:]
    candidates = [s]
    if "{" in s and "}" in s:
        candidates.append(s[s.find("{"):s.rfind("}") + 1])
    for c in candidates:
        try:
            o = json.loads(c)
            if isinstance(o, dict):
                return o, text
        except Exception:
            pass
    return None, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True)
    ap.add_argument("--family", required=True)
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing")

    packet_path = Path("review-inputs/v159-postfreeze") / f"{args.packet}.txt"
    packet = packet_path.read_text()
    baseline = BASELINE.read_text()
    model = load_model(args.family)
    usage_daily, budget_receipt = key_budget_status(key)
    if usage_daily is None:
        raise SystemExit("OpenRouter daily usage could not be verified")
    if usage_daily + PER_CALL_CEILING > DAILY_CEILING:
        raise SystemExit("OpenRouter daily reserved budget exhausted")
    packet_sha = sha(packet)
    prompt = build_prompt(packet, baseline, args.family, packet_sha)
    start = time.time()
    status, data, error = call(model, prompt, key)
    structured, raw_text = parse_content(data)
    result = {
        "schema": "GardenV159PostFreezeBlindReview/v1",
        "packet": args.packet,
        "packet_sha256": packet_sha,
        "family": args.family,
        "governed_model": model,
        "prompt_sha256": sha(prompt),
        "http_status": status,
        "error": error,
        "elapsed_seconds": round(time.time() - start, 2),
        "usable": bool(structured is not None or len(raw_text) >= 150),
        "review": structured,
        "raw_review": None if structured is not None else raw_text,
        "actual_model": (data or {}).get("model") if isinstance(data, dict) else None,
        "provider": (data or {}).get("provider") if isinstance(data, dict) else None,
        "usage": (data or {}).get("usage") if isinstance(data, dict) else None,
        "daily_budget_receipt": budget_receipt,
        "canonical_effect": False,
        "semantic_delta_admitted": False
    }
    outdir = OUT / args.packet
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{args.family}.json"
    cost = ((data or {}).get("usage") or {}).get("cost") if isinstance(data, dict) else None
    if isinstance(cost, (int, float)) and float(cost) > PER_CALL_CEILING:
        result["usable"] = False
        result["error"] = "MODEL_COST_CEILING_EXCEEDED"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"packet": args.packet, "family": args.family, "usable": result["usable"], "error": error}))
    if not result["usable"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
