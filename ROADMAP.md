# Garden Public Roadmap

This roadmap is for the public Garden swarm repository. It does not change canonical Garden semantics and does not imply machine, empirical, domain, or deployment certification.

## Completed public-enablement work

- Public five-file v15.5 source + manifest + release.
- Protected `main`, release-integrity CI, contribution/security/citation files.
- 60-minute evaluation protocol, evaluation log, roadmap, glossary and prior-art guide.
- Machine-readable `AGENTS.md`, `llms.txt`, discovery metadata and read-only integration specs.
- Read-only discovery-server foundation under `server/` with tests/CI.
- Non-certified executable reference prototype for ActionGate, authority composition, DesignEpoch invalidation and signed delegation receipts.
- Automated adversarial fixtures for shared-memory taint escalation, authority amplification and stale semantic bindings.

## P0 — make Garden executable and independently testable

1. **Minimal executable GSL kernel** — typed objects, authority/effect semantics, invariant checking, explicit UNKNOWN/STALE/BLOCKED states.
2. **Source-to-obligation compiler** — extract requirements, dependencies, proof/test obligations and unresolved gaps from the five-file source without inventing semantics.
3. **Expand adversarial evaluation harness** — convert each serious public finding into reproducible fixtures, fuzz/property tests and regression cases.
4. **Live A2A / MCP discovery relay** — deploy the safe read-only discovery server on public HTTPS, then add current conformant A2A/MCP bindings and register only after conformance/abuse controls pass.
5. **Reference-closure reproducer** — independently reproduce the current source/reference closure receipt.
6. **Package the executable reference cleanly** — evolve `prototype/` toward independently installable modules only where interfaces stabilize; do not split packages merely for branding.

## P1 — harden the constitutional/runtime boundary

1. Move the reference ActionGate toward an independently testable external runtime boundary with explicit authoritative stores and revocation/freshness inputs.
2. Extend capability/delegation/swarm no-amplification checks with path-level trace reconstruction, parent-budget persistence and split-action composition tests.
3. Extend prompt/retrieval/shared-memory taint propagation and plan/action separation tests beyond the current minimal regression fixture.
4. Implement consent-validity assessment with explicit UNKNOWN/INCONCLUSIVE semantics for voluntariness/comprehension where required.
5. Normalize emergency-trigger source-independence semantics and add common-mode/manufactured-urgency tests.
6. Produce deployment-oriented evidence that protected R0/R1 roots, stores and checker inputs are outside R2/R3 writable authority.
7. Add control evaluations that explicitly assume a strategically subverted proposer.

The current next-successor hardening candidate is tracked in issue #17.

## P2 — independent implementations and comparisons

1. Clean-room implementation of the minimal Garden control substrate.
2. Compare Garden mechanisms against capability-security, formal-policy, Constitutional AI, AI Control, corrigibility/off-switch and organizational risk frameworks such as NIST AI RMF.
3. Publish negative results and failed attacks alongside successful tests.
4. Build benchmark cases for privacy, justice, community governance, authority composition and stale-semantic handling.
5. Publish monthly adversarial-evaluation summaries once there is enough external activity to justify them.
6. Submit technical writeups to serious research/developer venues after runnable evidence exists.

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
