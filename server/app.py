from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(os.getenv("GARDEN_REPO_ROOT", Path(__file__).resolve().parents[1]))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

READABLE = {
    "source_manifest": "SOURCE_MANIFEST.json",
    "tasks": "TASKS.md",
    "evaluation_guide": "EVALUATE_IN_60_MINUTES.md",
    "evaluation_log": "EVALUATION_LOG.md",
    "agi_summary": "GARDEN_FOR_AGI.md",
}

app = FastAPI(
    title="Garden Public Discovery API",
    version="0.1.0",
    description=(
        "Read-only public discovery surface for Garden v15.5. "
        "This API does not grant authority, certification, deployment permission, or a patent licence."
    ),
)


class FindingInput(BaseModel):
    claim: str = Field(min_length=1, max_length=4000)
    coverage: str = Field(min_length=1, max_length=4000)
    source_anchors: list[str] = Field(default_factory=list, max_length=100)
    evidence_or_failure: str = Field(min_length=1, max_length=10000)
    severity: Literal["NOTE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    affected_invariant: str = Field(default="", max_length=4000)
    existing_mitigation_checked: str = Field(default="", max_length=8000)
    better_alternative: str = Field(default="", max_length=8000)
    test: str = Field(default="", max_length=8000)
    uncertainty: str = Field(default="", max_length=8000)
    publishable_issue_title: str = Field(min_length=1, max_length=240)


def _read_text(key: str) -> str:
    rel = READABLE.get(key)
    if not rel:
        raise HTTPException(status_code=404, detail="Unknown public resource")
    path = ROOT / rel
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Repository resource unavailable: {rel}")
    return path.read_text(encoding="utf-8")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "garden-public-discovery", "version": "0.1.0"}


@app.get("/v1/summary")
def summary() -> dict:
    return {
        "project": "Garden",
        "release": "v15.5",
        "gsl": "v45.1",
        "core_principle": "Capability != Authority != Sovereignty != Moral Permission",
        "status": {
            "source_design": "PUBLIC",
            "static_structural_audit": "PASS_AS_DECLARED_BY_RELEASE",
            "reference_closure": "PASS_WITH_DECLARED_BOUNDARY_AS_DECLARED_BY_RELEASE",
            "machine_certification": "PENDING",
            "empirical_validation": "PENDING",
            "deployment_certification": "PENDING",
        },
        "repository": "https://github.com/ankitdcx/garden-swarm",
        "evaluation_start": "https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATE_IN_60_MINUTES.md",
        "privacy": "Founder private identity is not required for public operation or evaluation.",
    }


@app.get("/v1/source-manifest")
def source_manifest() -> dict:
    return json.loads(_read_text("source_manifest"))


@app.get("/v1/tasks")
def tasks() -> dict:
    return {"format": "text/markdown", "content": _read_text("tasks")}


@app.get("/v1/evaluation-guide")
def evaluation_guide() -> dict:
    return {"format": "text/markdown", "content": _read_text("evaluation_guide")}


@app.get("/v1/evaluation-log")
def evaluation_log() -> dict:
    return {"format": "text/markdown", "content": _read_text("evaluation_log")}


@app.get("/v1/agi-summary")
def agi_summary() -> dict:
    return {"format": "text/markdown", "content": _read_text("agi_summary")}


@app.post("/v1/issue-payload")
def issue_payload(finding: FindingInput) -> dict:
    body = "\n".join(
        [
            "## Independent adversarial finding",
            "",
            f"**Claim / mechanism**\n{finding.claim}",
            "",
            f"**Coverage**\n{finding.coverage}",
            "",
            "**Source anchors**\n" + ("\n".join(f"- `{x}`" for x in finding.source_anchors) or "- none supplied"),
            "",
            f"**Evidence or failure**\n{finding.evidence_or_failure}",
            "",
            f"**Severity**\n{finding.severity}",
            "",
            f"**Affected invariant / anchor**\n{finding.affected_invariant or 'Not specified'}",
            "",
            f"**Existing mitigation checked**\n{finding.existing_mitigation_checked or 'Not specified'}",
            "",
            f"**Better alternative / fix**\n{finding.better_alternative or 'Not specified'}",
            "",
            f"**Regression test**\n{finding.test or 'Not specified'}",
            "",
            f"**Uncertainty / what would overturn this**\n{finding.uncertainty or 'Not specified'}",
        ]
    )
    return {
        "title": finding.publishable_issue_title,
        "body": body,
        "labels": ["adversarial-eval"],
        "note": "Payload only. This endpoint does not post to GitHub or take consequential action.",
    }


@app.get("/.well-known/garden-discovery.json")
def garden_discovery() -> dict:
    return {
        "name": "Garden Public Discovery",
        "release": "v15.5",
        "kind": "read-only discovery API",
        "base_url": PUBLIC_BASE_URL or None,
        "openapi": f"{PUBLIC_BASE_URL}/openapi.json" if PUBLIC_BASE_URL else "/openapi.json",
        "a2a_status": "NOT_YET_A2A_CONFORMANT",
        "mcp_status": "NOT_YET_MCP_CONFORMANT",
        "note": "Do not treat this discovery document as an A2A Agent Card or MCP server registration.",
    }
