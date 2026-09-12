# Contributing to Garden

Garden welcomes skeptical, reproducible contributions from humans and AI agents.

## Best contributions

Preferred contributions include:

- a concrete defect or counterexample;
- a proof or failed-proof result;
- a reproducible benchmark or empirical result;
- a reference implementation with tests;
- an interoperability improvement;
- a privacy, rights, authority, safety, or security finding;
- a demonstrably better alternative with a migration path.

Praise without evidence is less useful than a small verified correction.

## Start with a bounded task

Read `TASKS.md` and the open task issues. If your work is large, open an issue first and define the smallest independently reviewable unit.

For a first contribution, `EVALUATE_IN_60_MINUTES.md` is the recommended entry point.

## Finding format

For design/audit findings, use:

`finding -> evidence/counterexample -> severity -> affected anchors/invariants -> proposed correction -> regression test -> rights/authority impact`

Keep observation, inference, simulation, proof, recommendation, authorization, and action distinct.

## Pull requests

A pull request should state:

1. the problem being solved;
2. what changed;
3. evidence/tests supporting the change;
4. affected Garden anchors/invariants/contracts;
5. known limitations or unresolved uncertainty;
6. whether the change affects rights, privacy, authority, safety, IP, or interoperability.

Do not silently rewrite canonical meaning for readability. Semantic changes must be explicit.

## Canonical source integrity

The five Garden v15.5 source files listed in `SOURCE_MANIFEST.json` are byte-identified public source artifacts. If a task requires changing canonical source, explain why and provide a successor/versioning plan rather than silently modifying v15.5 in place.

## AI-generated contributions

AI-generated work is welcome, but model output is not evidence merely because a model produced it. The contributor remains responsible for checking claims, provenance, tests, and scope.

## Safety and privacy

Do not contribute:

- secrets, credentials, private keys, or unnecessary personal data;
- malware or exploit payloads intended for unauthorized use;
- instructions for covert deployment, credential theft, surveillance, or security bypass;
- real-world harmful testing without valid authorization.

Security vulnerabilities should follow `SECURITY.md`.

## Rights / patent boundary

Read `PATENT_AND_USE_NOTICE.md` before implementation or downstream use. Public contribution or source availability does not create rights beyond the explicit terms that actually apply.

## Human-in-the-loop

Original-design-intent questions may be escalated through `RELAY_PROTOCOL.md`. An HITL answer is evidence of original intent where relevant; it is not automatic scientific, factual, legal, or political authority.
