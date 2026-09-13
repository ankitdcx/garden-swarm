#!/usr/bin/env python3
"""Garden heterogeneous audit swarm.

Dry-run is the default. `--live` explicitly enables OpenRouter calls.
This harness does not merge changes or grant model outputs authority.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_SOURCE_FILES = [
    "Garden_User_v15.5_FULL_2026-09-12.txt",
    "Garden_System_v15.5_FULL_2026-09-12.txt",
    "Garden_Technical_v15.5_FULL_2026-09-12.txt",
    "Garden_Annexure_v15.5_FULL_2026-09-12.txt",
    "Garden_Theories_v15.5_FULL_2026-09-12.txt",
]


@dataclass(frozen=True)
class Role:
    id: str
    name: str
    model: str
    objective: str
    lenses: list[str]
    tier: str = "standard"
    web: bool = False


@dataclass(frozen=True)
class WorkItem:
    id: str
    source_file: str
    source_sha256: str
    chunk_index: int
    chunk_count: int
    text: str


@dataclass
class RunResult:
    work_item: str
    role_id: str
    role_name: str
    requested_model: str
    returned_model: str | None
    status: str
    output: str | None = None
    annotations: list[dict[str, Any]] | None = None
    usage: dict[str, Any] | None = None
    error: str | None = None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_roles(path: Path, tier: str) -> list[Role]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    roles = [Role(**r) for r in payload["roles"]]
    if len({r.id for r in roles}) != len(roles):
        raise ValueError("Duplicate role id")
    if tier == "calibration":
        roles = [r for r in roles if r.tier == "calibration"]
    elif tier == "standard":
        roles = [r for r in roles if r.tier in {"calibration", "standard"}]
    return roles


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Deterministic paragraph-aware chunking. No inferred semantics."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for p in paragraphs:
        add = len(p) + 2
        if current and size + add > max_chars:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        if len(p) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current, size = [], 0
            chunks.extend(p[i : i + max_chars] for i in range(0, len(p), max_chars))
            continue
        current.append(p)
        size += add
    if current:
        chunks.append("\n\n".join(current))
    return chunks or [""]


def build_work_items(root: Path, filenames: list[str], max_chars: int) -> list[WorkItem]:
    items: list[WorkItem] = []
    for filename in filenames:
        path = root / filename
        if not path.exists():
            raise FileNotFoundError(f"Canonical source missing: {filename}")
        raw = path.read_bytes()
        sha = digest(raw)
        chunks = chunk_text(raw.decode("utf-8"), max_chars)
        for i, text in enumerate(chunks, 1):
            items.append(
                WorkItem(
                    id=f"{path.stem}:chunk-{i:03d}",
                    source_file=filename,
                    source_sha256=sha,
                    chunk_index=i,
                    chunk_count=len(chunks),
                    text=text,
                )
            )
    return items


def system_prompt(role: Role) -> str:
    return f"""You are the Garden audit role: {role.name}.
Objective: {role.objective}
Primary lenses: {", ".join(role.lenses)}

Rules:
- Do not praise Garden by default. Try to falsify, simplify, or improve it.
- Distinguish defect, missing evidence, implementation gap, obsolete assumption,
  unnecessary complexity, and genuinely new opportunity.
- Do not treat agreement or majority vote as proof.
- Never silently invent missing Garden semantics.
- A valid answer may be NO_CHANGE.
- If the suspected gap may be covered elsewhere, mark NEEDS_CROSS_REFERENCE.
- Separate source-supported facts from your inference.
- Return JSON only.

Return:
{{
  "summary": "...",
  "verdict": "NO_CHANGE|PATCH_CANDIDATE|BLOCKER|NEEDS_CROSS_REFERENCE",
  "findings": [
    {{
      "title": "...",
      "kind": "...",
      "severity": "INFO|LOW|MEDIUM|HIGH|CRITICAL",
      "current_claim": "...",
      "problem_or_opportunity": "...",
      "proposed_change": "...",
      "alternatives_considered": ["..."],
      "affected_anchors_or_terms": ["..."],
      "evidence_needed": ["..."],
      "regression_test": "...",
      "uncertainty": "...",
      "what_would_overturn": "..."
    }}
  ]
}}
"""


def user_prompt(item: WorkItem) -> str:
    return f"""Audit this frozen Garden v15.5 work package.

Source file: {item.source_file}
SHA-256: {item.source_sha256}
Chunk: {item.chunk_index}/{item.chunk_count}
Work item: {item.id}

Do not claim that something is absent from Garden merely because it is absent from
this chunk. Such claims require a later cross-reference pass.

--- BEGIN FROZEN SOURCE ---
{item.text}
--- END FROZEN SOURCE ---
"""


def call_openrouter(role: Role, item: WorkItem, max_tokens: int) -> RunResult:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return RunResult(item.id, role.id, role.name, role.model, None, "ERROR",
                         error="OPENROUTER_API_KEY is not set")

    payload: dict[str, Any] = {
        "model": role.model,
        "messages": [
            {"role": "system", "content": system_prompt(role)},
            {"role": "user", "content": user_prompt(item)},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "provider": {"zdr": True},
    }
    if role.web:
        payload["plugins"] = [{"id": "web", "engine": "parallel",
                               "mode": "turbo", "max_results": 5}]

    req = request.Request(
        OPENROUTER_URL,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ankitdcx/garden-swarm",
            "X-Title": "Garden Swarm",
        },
    )

    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
        msg = data["choices"][0]["message"]
        return RunResult(
            work_item=item.id,
            role_id=role.id,
            role_name=role.name,
            requested_model=role.model,
            returned_model=data.get("model"),
            status="OK",
            output=msg.get("content", ""),
            annotations=msg.get("annotations"),
            usage=data.get("usage"),
        )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1500]
        return RunResult(item.id, role.id, role.name, role.model, None, "ERROR",
                         error=f"HTTP {exc.code}: {detail}")
    except Exception as exc:
        return RunResult(item.id, role.id, role.name, role.model, None, "ERROR",
                         error=f"{type(exc).__name__}: {exc}")


def receipt(mode: str, roles: list[Role], items: list[WorkItem],
            results: list[RunResult], args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema": "GardenSwarmRunReceipt/v0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "garden_release": "v15.5",
        "source_identity": [
            {
                "work_item": w.id,
                "source_file": w.source_file,
                "source_sha256": w.source_sha256,
                "chunk_index": w.chunk_index,
                "chunk_count": w.chunk_count,
                "chars": len(w.text),
            }
            for w in items
        ],
        "roles": [asdict(r) for r in roles],
        "limits": {
            "max_chars": args.max_chars,
            "max_tokens": args.max_tokens,
            "max_calls": args.max_calls,
            "max_concurrency": args.max_concurrency,
        },
        "results": [asdict(r) for r in results],
        "admission_status": "PROPOSALS_ONLY",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--roles", default="swarm/roles.json")
    p.add_argument("--source", action="append", dest="sources")
    p.add_argument("--role-tier", choices=["calibration", "standard", "all"],
                   default="calibration")
    p.add_argument("--max-chars", type=int, default=60000)
    p.add_argument("--max-tokens", type=int, default=3000)
    p.add_argument("--max-calls", type=int, default=4)
    p.add_argument("--max-concurrency", type=int, default=2)
    p.add_argument("--live", action="store_true")
    p.add_argument("--output", default="swarm/runs/latest-plan.json")
    args = p.parse_args()

    root = Path(args.repo_root).resolve()
    roles = load_roles(root / args.roles, args.role_tier)
    items = build_work_items(root, args.sources or DEFAULT_SOURCE_FILES, args.max_chars)
    pairs = [(role, item) for item in items for role in roles]

    results: list[RunResult] = []
    if args.live:
        if not os.environ.get("OPENROUTER_API_KEY"):
            raise SystemExit("OPENROUTER_API_KEY is required for --live")
        selected = pairs[: args.max_calls]
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.max_concurrency
        ) as pool:
            futures = [
                pool.submit(call_openrouter, role, item, args.max_tokens)
                for role, item in selected
            ]
            for f in concurrent.futures.as_completed(futures):
                result = f.result()
                results.append(result)
                print(f"{result.status}: {result.role_id} / {result.work_item}")
        mode = "LIVE"
    else:
        print(
            f"DRY RUN: {len(roles)} roles x {len(items)} work items = "
            f"{len(pairs)} planned calls"
        )
        print("No OpenRouter request was sent.")
        mode = "DRY_RUN"

    data = receipt(mode, roles, items, results, args)
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"Receipt: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
