from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from server.mcp_service import mcp, streamable_http_app

ROOT = Path(os.getenv("GARDEN_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
_RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
PUBLIC_BASE_URL = (
    os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    or (f"https://{_RENDER_EXTERNAL_HOSTNAME}" if _RENDER_EXTERNAL_HOSTNAME else "")
)

READABLE = {
    "source_manifest": "SOURCE_MANIFEST.json",
    "tasks": "TASKS.md",
    "evaluation_guide": "EVALUATE_IN_60_MINUTES.md",
    "evaluation_log": "EVALUATION_LOG.md",
    "agi_summary": "GARDEN_FOR_AGI.md",
}


def _validated_root(root: Path) -> Path:
    """Require a Garden public-source snapshot rather than trusting an arbitrary root."""
    resolved = root.resolve()
    manifest = resolved / "SOURCE_MANIFEST.json"
    version = resolved / "VERSION"
    if not manifest.is_file() or not version.is_file():
        raise RuntimeError(
            "GARDEN_REPO_ROOT must contain SOURCE_MANIFEST.json and VERSION"
        )
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("GARDEN_REPO_ROOT has an unreadable source manifest") from exc
    if not data.get("release") or not isinstance(data.get("canonical_files"), list):
        raise RuntimeError("GARDEN_REPO_ROOT source manifest is not a recognized Garden release manifest")
    return resolved


ROOT = _validated_root(ROOT)
_mcp_http_app = streamable_http_app()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Mounted MCP ASGI apps do not run their own lifespan. The host application
    # must own the MCP session manager lifecycle.
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="Garden Public Discovery API",
    version="0.2.0",
    description=(
        "Read-only public discovery surface for Garden v15.5. "
        "This API does not grant authority, certification, deployment permission, or a patent licence."
    ),
    lifespan=lifespan,
)

# Official MCP Python SDK v2 Streamable HTTP endpoint. The mounted app uses
# streamable_http_path='/' so clients connect to /mcp/ (same-origin redirect
# from /mcp is acceptable to the official client).
app.mount("/mcp", _mcp_http_app)


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
    path = (ROOT / rel).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Repository resource escaped configured root") from exc
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"Repository resource unavailable: {rel}")
    return path.read_text(encoding="utf-8")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "garden-public-discovery", "version": "0.2.0"}


@app.get("/v1/summary")
def summary() -> dict:
    return {
        "project": "Garden",
        "release": "v15.5",
        "gsl": "v45.1",
        "core_principle": "Capability != Authority != Sovereignty != Moral Permission",
        "status": {
            "source_design": "PUBLIC",
            "static_structural_audit": "AUTHOR_SOURCE_SELF_AUDIT_PASS_WITHIN_DECLARED_BOUNDARY",
            "reference_closure": "AUTHOR_SOURCE_SELF_AUDIT_PASS_WITHIN_DECLARED_BOUNDARY",
            "machine_certification": "PENDING",
            "empirical_validation": "PENDING",
            "deployment_certification": "PENDING",
        },
        "repository": "https://github.com/ankitdcx/garden-swarm",
        "evaluation_start": "https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATE_IN_60_MINUTES.md",
        "mcp": {
            "implementation": "OFFICIAL_PYTHON_SDK_V2",
            "transport": "STREAMABLE_HTTP",
            "endpoint": f"{PUBLIC_BASE_URL}/mcp/" if PUBLIC_BASE_URL else "/mcp/",
            "public_conformance": "PENDING_LIVE_ENDPOINT_VERIFICATION",
        },
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
        "mcp": f"{PUBLIC_BASE_URL}/mcp/" if PUBLIC_BASE_URL else "/mcp/",
        "a2a_status": "NOT_YET_A2A_CONFORMANT",
        "mcp_status": "OFFICIAL_SDK_IMPLEMENTED_LOCAL_TEST_PENDING_PUBLIC_ENDPOINT_VERIFICATION",
        "note": "MCP is read-only and grants no external action authority. A2A Agent Card publication remains separate pending work.",
    }
