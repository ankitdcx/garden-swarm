from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

ROOT = Path(os.getenv("GARDEN_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
DESIGN_EPOCH_REF = "Garden-v15.5@63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598"
MCP_ENVELOPE_ID = "AGENT-ENVELOPE-GARDEN-PUBLIC-MCP-v1"
DECLARED_MCP_TOOLS = frozenset({
    "current_release",
    "list_attack_surfaces",
    "evaluation_instructions",
    "public_tasks",
    "build_finding_payload",
})

mcp = MCPServer(
    "Garden Public Discovery",
    version="0.1.0",
)


def _validated_root(root: Path) -> Path:
    resolved = root.resolve()
    manifest = resolved / "SOURCE_MANIFEST.json"
    version = resolved / "VERSION"
    if not manifest.is_file() or not version.is_file():
        raise RuntimeError("GARDEN_REPO_ROOT must contain SOURCE_MANIFEST.json and VERSION")
    return resolved


ROOT = _validated_root(ROOT)


def _read(rel: str) -> str:
    path = (ROOT / rel).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(f"Public Garden resource escaped configured root: {rel}") from exc
    if not path.is_file():
        raise RuntimeError(f"Public Garden resource unavailable: {rel}")
    return path.read_text(encoding="utf-8")


def _load_mcp_envelope() -> dict[str, Any]:
    payload = json.loads(_read("gsl/AGENT_ENVELOPES.json"))
    if payload.get("schema") != "GardenAgentEnvelopeRegistry/v1":
        raise RuntimeError("Garden MCP AgentEnvelope registry schema is not recognized")
    if payload.get("design_epoch_ref") != DESIGN_EPOCH_REF:
        raise RuntimeError("Garden MCP AgentEnvelope is stale for the active DesignEpoch")
    envelopes = payload.get("envelopes") or []
    envelope = next((x for x in envelopes if x.get("envelope_id") == MCP_ENVELOPE_ID), None)
    if envelope is None:
        raise RuntimeError("Garden public MCP AgentEnvelope is missing")
    allowlist = frozenset(str(x) for x in envelope.get("tool_allowlist") or [])
    if allowlist != DECLARED_MCP_TOOLS:
        raise RuntimeError(
            f"Garden public MCP tool/envelope mismatch: tools={sorted(DECLARED_MCP_TOOLS)} "
            f"allowlist={sorted(allowlist)}"
        )
    authority = envelope.get("authority") or {}
    prohibited = ("github_write", "deployment", "canonical_promotion", "real_world_actuation")
    if any(bool(authority.get(name)) for name in prohibited):
        raise RuntimeError("Garden public MCP envelope grants prohibited authority")
    if (envelope.get("delegation") or {}).get("allowed") is not False:
        raise RuntimeError("Garden public MCP envelope must forbid delegation")
    if envelope.get("runtime_enforcement") is None:
        raise RuntimeError("Garden public MCP envelope lacks invocation-time enforcement declaration")
    return envelope


def _assert_tool_invocation(tool_name: str, *, resource: str | None = None, text_values: tuple[str, ...] = ()) -> dict[str, Any]:
    """Re-evaluate the current AgentEnvelope at call time, not only at startup."""
    envelope = _load_mcp_envelope()
    allowlist = set(envelope.get("tool_allowlist") or [])
    if tool_name not in allowlist:
        raise RuntimeError(f"MCP tool no longer authorized by current AgentEnvelope: {tool_name}")
    if resource is not None and resource not in set(envelope.get("resources") or []):
        raise RuntimeError(f"MCP resource outside current AgentEnvelope: {resource}")
    constraints = (envelope.get("tool_constraints") or {}).get(tool_name) or {}
    if text_values:
        max_total = constraints.get("max_total_text_chars")
        if max_total is None:
            raise RuntimeError(f"MCP text-bearing tool lacks declared input bound: {tool_name}")
        if sum(len(value) for value in text_values) > int(max_total):
            raise ValueError(f"MCP invocation exceeds AgentEnvelope text bound for {tool_name}")
    return envelope


MCP_AGENT_ENVELOPE = _load_mcp_envelope()


def _public_host_and_port() -> tuple[str | None, int | None]:
    explicit = os.getenv("PUBLIC_BASE_URL", "").strip()
    if explicit:
        parsed = urlparse(explicit if "://" in explicit else f"https://{explicit}")
        if parsed.hostname:
            return parsed.hostname, parsed.port
    render = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    return (render or None), None


def transport_security() -> TransportSecuritySettings:
    hosts = ["127.0.0.1:*", "localhost:*", "testserver:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://testserver:*"]
    public_host, public_port = _public_host_and_port()
    if public_host:
        hosts.append(f"{public_host}:{public_port}" if public_port else public_host)
        origin = f"https://{public_host}"
        if public_port and public_port != 443:
            origin += f":{public_port}"
        origins.append(origin)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def streamable_http_app():
    """Return the official MCP v2 Streamable HTTP ASGI app under the declared read-only envelope."""
    return mcp.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        transport_security=transport_security(),
    )


@mcp.tool()
def current_release() -> dict[str, Any]:
    """Return Garden's current public release identity and assurance boundary."""
    _assert_tool_invocation("current_release", resource="SOURCE_MANIFEST.json")
    manifest = json.loads(_read("SOURCE_MANIFEST.json"))
    return {
        "project": "Garden",
        "release": manifest.get("release", "Garden-v15.5-2026-09-12"),
        "gsl": manifest.get("gsl", "v45.1"),
        "design_epoch_ref": DESIGN_EPOCH_REF,
        "agent_envelope_ref": MCP_ENVELOPE_ID,
        "core_principle": "Capability != Authority != Sovereignty != Moral Permission",
        "status": manifest.get("status", {}),
        "repository": "https://github.com/ankitdcx/garden-swarm",
        "note": "Public discovery only; this result grants no authority, certification, deployment permission, or patent licence.",
    }


@mcp.tool()
def list_attack_surfaces() -> str:
    """Return the public mechanism-indexed adversarial attack menu."""
    _assert_tool_invocation("list_attack_surfaces", resource="ATTACK_SURFACE.md")
    return _read("ATTACK_SURFACE.md")


@mcp.tool()
def evaluation_instructions() -> str:
    """Return Garden's structured independent-evaluation protocol."""
    _assert_tool_invocation("evaluation_instructions", resource="EVALUATE_IN_60_MINUTES.md")
    return _read("EVALUATE_IN_60_MINUTES.md")


@mcp.tool()
def public_tasks() -> str:
    """Return the public Garden task queue."""
    _assert_tool_invocation("public_tasks", resource="TASKS.md")
    return _read("TASKS.md")


@mcp.tool()
def build_finding_payload(
    claim: str,
    coverage: str,
    evidence_or_failure: str,
    severity: str,
    source_anchors: str = "",
    affected_invariant: str = "",
    existing_mitigation_checked: str = "",
    better_alternative: str = "",
    test: str = "",
    uncertainty: str = "",
    publishable_issue_title: str = "",
) -> dict[str, str]:
    """Build a publication-ready adversarial finding payload without posting it."""
    values = (
        claim, coverage, evidence_or_failure, severity, source_anchors,
        affected_invariant, existing_mitigation_checked, better_alternative,
        test, uncertainty, publishable_issue_title,
    )
    envelope = _assert_tool_invocation("build_finding_payload", text_values=values)
    constraints = (envelope.get("tool_constraints") or {}).get("build_finding_payload") or {}
    allowed = set(constraints.get("severity_allowlist") or [])
    normalized = severity.upper().strip()
    if normalized not in allowed:
        raise ValueError(f"severity must be one of {sorted(allowed)}")
    title = publishable_issue_title.strip() or f"[Adversarial finding] {claim.strip()[:160]}"
    body = "\n\n".join(
        [
            f"**Claim / mechanism**\n{claim.strip()}",
            f"**Coverage**\n{coverage.strip()}",
            f"**Source anchors**\n{source_anchors.strip() or 'Not supplied'}",
            f"**Evidence or failure**\n{evidence_or_failure.strip()}",
            f"**Severity**\n{normalized}",
            f"**Affected invariant / anchor**\n{affected_invariant.strip() or 'Not supplied'}",
            f"**Existing mitigation checked**\n{existing_mitigation_checked.strip() or 'Not supplied'}",
            f"**Better alternative / fix**\n{better_alternative.strip() or 'Not supplied'}",
            f"**Regression test**\n{test.strip() or 'Not supplied'}",
            f"**Uncertainty / what would overturn this**\n{uncertainty.strip() or 'Not supplied'}",
        ]
    )
    return {
        "title": title,
        "body": body,
        "note": "Payload only. No GitHub write, external action, or authority grant occurs.",
    }


@mcp.resource("garden://source-manifest")
def source_manifest_resource() -> str:
    """Canonical public release manifest and source hashes."""
    return _read("SOURCE_MANIFEST.json")


@mcp.resource("garden://attack-surfaces")
def attack_surface_resource() -> str:
    """Public Garden attack-surface menu."""
    return _read("ATTACK_SURFACE.md")


@mcp.resource("garden://evaluation-log")
def evaluation_log_resource() -> str:
    """Public index of adversarial findings and full-source triage."""
    return _read("EVALUATION_LOG.md")
