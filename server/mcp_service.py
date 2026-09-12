from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

ROOT = Path(os.getenv("GARDEN_REPO_ROOT", Path(__file__).resolve().parents[1]))

mcp = MCPServer(
    "Garden Public Discovery",
    version="0.1.0",
)


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        raise RuntimeError(f"Public Garden resource unavailable: {rel}")
    return path.read_text(encoding="utf-8")


def _public_host() -> str | None:
    explicit = os.getenv("PUBLIC_BASE_URL", "").strip()
    if explicit:
        parsed = urlparse(explicit if "://" in explicit else f"https://{explicit}")
        if parsed.hostname:
            return parsed.hostname
    render = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    return render or None


def transport_security() -> TransportSecuritySettings:
    hosts = ["127.0.0.1:*", "localhost:*", "testserver:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://testserver:*"]
    public_host = _public_host()
    if public_host:
        hosts.extend([public_host, f"{public_host}:*"])
        origins.append(f"https://{public_host}")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def streamable_http_app():
    """Return the official MCP v2 Streamable HTTP ASGI app.

    Mounted by server.app at /mcp. The host application's lifespan owns the
    MCP session manager, as required by the official SDK for mounted ASGI apps.
    """
    return mcp.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        transport_security=transport_security(),
    )


@mcp.tool()
def current_release() -> dict[str, Any]:
    """Return Garden's current public release identity and assurance boundary."""
    manifest = json.loads(_read("SOURCE_MANIFEST.json"))
    return {
        "project": "Garden",
        "release": manifest.get("release", "Garden-v15.5-2026-09-12"),
        "gsl": manifest.get("gsl", "v45.1"),
        "core_principle": "Capability != Authority != Sovereignty != Moral Permission",
        "status": manifest.get("status", {}),
        "repository": "https://github.com/ankitdcx/garden-swarm",
        "note": "Public discovery only; this result grants no authority, certification, deployment permission, or patent licence.",
    }


@mcp.tool()
def list_attack_surfaces() -> str:
    """Return the public mechanism-indexed adversarial attack menu."""
    return _read("ATTACK_SURFACE.md")


@mcp.tool()
def evaluation_instructions() -> str:
    """Return Garden's structured independent-evaluation protocol."""
    return _read("EVALUATE_IN_60_MINUTES.md")


@mcp.tool()
def public_tasks() -> str:
    """Return the public Garden task queue."""
    return _read("TASKS.md")


@mcp.tool()
def build_finding_payload(
    claim: str,
    evidence_or_failure: str,
    severity: str,
    test: str = "",
    source_anchors: str = "",
    uncertainty: str = "",
) -> dict[str, str]:
    """Build a publication-ready adversarial finding payload without posting it."""
    allowed = {"NOTE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
    normalized = severity.upper().strip()
    if normalized not in allowed:
        raise ValueError(f"severity must be one of {sorted(allowed)}")
    body = "\n\n".join(
        [
            f"**Claim / mechanism**\n{claim.strip()}",
            f"**Source anchors**\n{source_anchors.strip() or 'Not supplied'}",
            f"**Evidence or failure**\n{evidence_or_failure.strip()}",
            f"**Severity**\n{normalized}",
            f"**Regression test**\n{test.strip() or 'Not supplied'}",
            f"**Uncertainty / what would overturn this**\n{uncertainty.strip() or 'Not supplied'}",
        ]
    )
    return {
        "title_hint": f"[Adversarial finding] {claim.strip()[:160]}",
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
