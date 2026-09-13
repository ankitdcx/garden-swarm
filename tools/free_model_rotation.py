#!/usr/bin/env python3
"""Select diverse OpenRouter :free model families for the hourly Garden review."""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

CATALOG = "https://openrouter.ai/api/v1/models"
FAMILIES = [
    ("deepseek", ("deepseek/",), "formal"),
    ("qwen", ("qwen/",), "implementation"),
    ("llama", ("meta-llama/", "meta/"), "open_weight_baseline"),
    ("mistral", ("mistralai/",), "compliance"),
    ("glm", ("z-ai/", "zhipu/", "zhipuai/", "thudm/"), "formal"),
    ("gemma", ("google/gemma",), "open_weight_baseline"),
    ("cohere", ("cohere/",), "grounding"),
    ("nvidia", ("nvidia/",), "adversary"),
    ("dots", ("dots-studio/",), "formal"),
    ("inkling", ("thinking-machines/",), "grounding"),
]


def catalog(key: str) -> list[dict]:
    req = request.Request(CATALOG, headers={"Authorization": f"Bearer {key}"})
    with request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return [x for x in data.get("data", []) if str(x.get("id", "")).endswith(":free")]


def choose(models: list[dict], slot: int, count: int = 2) -> list[dict]:
    out = []
    for off in range(len(FAMILIES)):
        family, prefixes, role = FAMILIES[(slot + off) % len(FAMILIES)]
        hits = [m for m in models if any(str(m.get("id", "")).startswith(p) for p in prefixes)]
        if not hits:
            continue
        hits.sort(key=lambda m: int(m.get("context_length") or 0), reverse=True)
        model = hits[0]
        out.append({"family": family, "role": role, "model": model["id"],
                    "context_length": model.get("context_length")})
        if len(out) == count:
            return out
    raise SystemExit("Could not resolve two diverse :free model families from the live catalog")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="agents/runtime/free-selection.json")
    p.add_argument("--slot", type=int)
    args = p.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    slot = args.slot if args.slot is not None else int(datetime.now(timezone.utc).timestamp() // 3600)
    models = catalog(key)
    picked = choose(models, slot)
    payload = {"schema": "GardenFreeModelSelection/v1", "hour_slot": slot,
               "free_catalog_count": len(models), "selected": picked}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
