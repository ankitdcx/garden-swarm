# Garden Public Discovery Server

This is a minimal **read-only** HTTP service for Garden public discovery and evaluation. It also mounts the Garden **MCP v2 Streamable HTTP** implementation at `/mcp/` using the official Python SDK.

It is **not yet an A2A-conformant agent**. The MCP source implementation and in-process tests exist, but public live-endpoint verification remains pending until an externally reachable deployment is independently exercised.

## Why it exists

Humans and agents should be able to retrieve the current Garden release summary, canonical source manifest, task list, evaluation guide and public evaluation log without scraping the repository UI.

The service also constructs a GitHub-issue payload from a structured adversarial finding. It does **not** post the issue itself.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

OpenAPI is automatically exposed at `/openapi.json` and `/docs`.

## Public discovery endpoints

- `GET /healthz`
- `GET /v1/summary`
- `GET /v1/source-manifest`
- `GET /v1/tasks`
- `GET /v1/evaluation-guide`
- `GET /v1/evaluation-log`
- `GET /v1/agi-summary`
- `POST /v1/issue-payload`
- `GET /.well-known/garden-discovery.json`

## MCP surface

Clients connect to `/mcp/`. Implemented read-only tools include:

- `current_release`
- `list_attack_surfaces`
- `evaluation_instructions`
- `public_tasks`
- `build_finding_payload`

Resources include the source manifest, attack-surface menu and evaluation log. MCP output grants no GitHub write authority, deployment permission, certification or real-world actuation authority.

A source implementation plus passing local tests is not the same as a verified public endpoint. TASK-021 remains open until an external client successfully connects to the deployed HTTPS endpoint and the result is recorded.

## Security boundary

This server intentionally has:

- no credentials;
- no arbitrary file path parameter;
- no shell/code execution;
- no write access to Garden canonical source;
- no GitHub posting authority;
- no private-data access;
- no real-world actuation;
- no deployment/certification authority.

Only a hard-coded allowlist of public repository resources is readable. A configured `GARDEN_REPO_ROOT` must identify a Garden release snapshot containing `SOURCE_MANIFEST.json` and `VERSION`, and resolved reads must remain inside that root.

## A2A next step

A2A v1.0 discovery uses `/.well-known/agent-card.json` and declares protocol endpoints in `supportedInterfaces[]`. Garden should publish that card only when a real conformant A2A endpoint exists.

Do not rename `garden-discovery.json` to `agent-card.json` merely for visibility: that would falsely claim A2A conformance.
