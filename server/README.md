# Garden Public Discovery Server

This is a minimal **read-only** HTTP service for Garden public discovery and evaluation.

It is a stepping stone toward TASK-021. It is **not yet an A2A-conformant agent** and **not yet an MCP-conformant server**.

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

## Public endpoints

- `GET /healthz`
- `GET /v1/summary`
- `GET /v1/source-manifest`
- `GET /v1/tasks`
- `GET /v1/evaluation-guide`
- `GET /v1/evaluation-log`
- `GET /v1/agi-summary`
- `POST /v1/issue-payload`
- `GET /.well-known/garden-discovery.json`

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

Only a hard-coded allowlist of public repository resources is readable.

## A2A / MCP next step

A2A v1.0 discovery uses `/.well-known/agent-card.json` and declares protocol endpoints in `supportedInterfaces[]`. Garden should publish that card only when a real conformant A2A endpoint exists.

For MCP, remote deployment should use a current Streamable HTTP implementation and be tested against the then-current protocol/registry requirements before registration.

Do not rename `garden-discovery.json` to `agent-card.json` merely for visibility: that would falsely claim A2A conformance.
