# Garden v15.9 Semantic KB — Source-State Findings

This file records source-declared incompleteness separately from semantic extraction completeness.

## Release-level status
v15.9 declares itself a COMPLETE DOCUMENTATION-REWRITE WORKING CANDIDATE, not canonical unless separately admitted. Machine/executable/empirical/external certification is not implied.

## Non-PASS semantics are first-class
CURRENT status is distinct from CANDIDATE, DEFERRED, RESEARCH and MACHINE_BINDING_INCOMPLETE.
UNKNOWN, STALE, CONFLICT, BLOCKED, INCOMPLETE and NEEDS_REVALIDATION remain non-PASS wherever hard resolution is required.

## Machine-binding incompleteness
The Technical source contains requirement profiles whose semantic contracts exist but whose machine-resolvable FunctionContract identity/binding remains unresolved. Examples include deferred product selections and supply-chain/TUF/in-toto profiles. These must not be normalized into executable PASS merely because the semantic requirement is clear.

## Pending qualification
Some ratified/additive semantic profiles explicitly state that machine proof, empirical qualification, fallback-controller qualification or implementation evidence remains PENDING.

## Reference closure
ReferenceClosureReceipt PASS requires zero unresolved current normative references inside the declared release boundary. Historical imports/migrations are version-bound and cannot become current authority by alias.

## Consequence for the Semantic KB
The KB may be semantically complete as an extraction of what v15.9 states while v15.9 itself still contains deliberately incomplete execution/certification bindings. These are not extraction gaps; they are semantics saying 'not yet executable/certified'.

Therefore the semantic KB must preserve:
- semantic rule;
- controlling owner;
- status;
- executable-binding status;
- proof/validation/certification status;
- invalidators and dependencies;
rather than collapsing all statements to undifferentiated rules.
