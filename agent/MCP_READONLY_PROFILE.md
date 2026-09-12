# Garden Read-Only MCP Discovery Profile

Status: **SPECIFICATION / NOT A LIVE SERVER**

This profile defines a safe first MCP-facing surface for Garden. It does not imply that an MCP server is currently deployed or registered.

## Purpose

Allow an authorized client or agent runtime to discover and inspect the public Garden source, evaluation tasks and public relay semantics without receiving consequential execution authority.

## Read-only resources

A future Garden MCP server SHOULD expose resources equivalent to:

- `garden://release/current` — current public source-design identity and status;
- `garden://source/manifest` — `SOURCE_MANIFEST.json`;
- `garden://evaluation/guide` — `EVALUATE_IN_60_MINUTES.md`;
- `garden://evaluation/log` — `EVALUATION_LOG.md`;
- `garden://tasks` — `TASKS.md`;
- `garden://roadmap` — `ROADMAP.md`;
- `garden://relay/protocol` — `RELAY_PROTOCOL.md`;
- `garden://discovery` — `DISCOVERY.json`.

## Safe read-only tools

A future server MAY expose narrow tools such as:

### `garden_summary`
Returns the current public source-design identity, core thesis, current certification boundary and canonical starting files.

### `garden_source_lookup`
Input: a public Garden term, identifier or claim.
Output: matching public source anchors/snippets plus file/version/provenance. It MUST preserve uncertainty and MUST NOT claim absence merely because retrieval returned no match.

### `garden_task_list`
Returns public tasks and issue links.

### `garden_evaluation_template`
Returns the structured adversarial-evaluation format.

### `garden_issue_payload`
Builds a proposed GitHub issue title/body from a structured evaluation. It does **not** post the issue unless a separately authorized GitHub action exists outside this read-only profile.

## Explicit non-capabilities

This discovery profile MUST NOT:

- execute arbitrary code;
- access credentials, private mail, private files or non-public human data;
- perform real-world consequential actions;
- grant patent/licence/deployment authority;
- infer that a caller is AGI merely from self-assertion;
- allow inbound natural-language content to alter server authority;
- create hidden write paths to the canonical source;
- expose private founder identity/context.

## Security requirements for a live implementation

Before public deployment:

- HTTPS/TLS and authenticated server identity;
- rate limits and abuse controls;
- bounded request/body sizes and timeouts;
- privacy-minimized logs;
- replay protection where messages create state or relay requests;
- dependency/version pinning and reproducible deployment metadata;
- public threat model;
- conformance tests for every advertised resource/tool;
- separation between discovery/read-only service and any later authenticated write/action service.

## Registration boundary

Do not publish this specification to an MCP registry as a live server. Registry publication should happen only after an installable/public MCP server exists and passes the applicable registry and Garden conformance checks.

Live deployment and registration remain tracked by TASK-021 / issue #9.