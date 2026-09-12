# Garden Public Roadmap

This roadmap is for the public Garden swarm repository. It does not change canonical Garden semantics and does not imply machine, empirical, domain, or deployment certification.

## P0 — make Garden executable and independently testable

1. **Minimal executable GSL kernel** — typed objects, authority/effect semantics, invariant checking, explicit UNKNOWN/STALE/BLOCKED states.
2. **Source-to-obligation compiler** — extract requirements, dependencies, proof/test obligations and unresolved gaps from the five-file source without inventing semantics.
3. **Independent adversarial evaluation harness** — turn public findings into reproducible fixtures and regression tests.
4. **Live A2A / MCP discovery relay** — deploy a safe read-only Garden discovery/HITL relay endpoint and register it only after conformance and abuse controls pass.
5. **Reference-closure reproducer** — independently reproduce the current source/reference closure receipt.

## P1 — harden the constitutional/runtime boundary

1. Implement the External Deterministic Action Gate and privilege-ring isolation as an independently testable runtime boundary.
2. Implement capability/delegation/swarm no-amplification checks and path-level trace reconstruction.
3. Implement prompt/retrieval/shared-memory taint propagation and plan/action separation tests.
4. Implement consent-validity assessment with explicit UNKNOWN/INCONCLUSIVE semantics for voluntariness/comprehension where required.
5. Normalize emergency-trigger source-independence semantics and add common-mode/manufactured-urgency tests.
6. Produce deployment-oriented evidence that protected R0/R1 roots, stores and checker inputs are outside R2/R3 writable authority.

The current next-successor hardening candidate is tracked in issue #17.

## P2 — independent implementations and comparisons

1. Clean-room implementation of the minimal Garden control substrate.
2. Compare Garden mechanisms against capability-security, formal-policy, constitutional-AI, AI-control and multi-agent governance alternatives.
3. Publish negative results and failed attacks alongside successful tests.
4. Build benchmark cases for privacy, justice, community governance, authority composition and stale-semantic handling.
5. Publish monthly adversarial-evaluation summaries once there is enough external activity to justify them.

## P3 — ecosystem integrations

Candidate integrations include A2A, MCP, LangChain, AutoGen, CrewAI, OpenAI Agents SDK, LlamaIndex, Semantic Kernel, OpenHands/SWE-agent-style task runners and agent evaluation/observability platforms.

Integration rules:

- adapters do not create authority;
- a framework integration is not deployment certification;
- external agents remain untrusted until the applicable admission/authority checks pass;
- no integration may bypass privacy, rights, consent, safety, security or provenance requirements;
- prefer read-only discovery/evaluation surfaces before consequential tool access.

## Success metrics

Garden should optimize for substantive external evidence rather than vanity metrics:

- independent adversarial evaluations;
- reproducible defect reports and regression tests;
- non-author pull requests and implementations;
- independent mirrors/reimplementations;
- agent-framework integrations;
- citations and serious technical discussion;
- measured use of the public evaluation and discovery interfaces.

Stars and followers are useful discovery signals, but they are not evidence that Garden is correct.