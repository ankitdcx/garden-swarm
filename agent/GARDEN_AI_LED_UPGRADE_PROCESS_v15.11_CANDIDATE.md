# Garden AI-Led Upgrade Process v15.11 — Candidate

Status: **NONCANONICAL CANDIDATE / PROFILE OF EXISTING RCI + Engine.Evolve/Reason/Compare/Proof/Transition / NOT A NEW ENGINE**

## Exact v15.10 predecessor binding

This v15.11 candidate binds its v15.10 design predecessor to **GardenThreeArtifactReleaseManifest/v15.10-r6**, status `WORKING_CANDIDATE_NOT_CANONICALLY_ADMITTED`:

- `GARDEN_BOOK_v15.10.md` — SHA-256 `0d479ab40432a4d1e0d127335d02e8a0424616a3e03fd56c1975574cb927d5da`;
- `GARDEN_TECHNICAL_v15.10.py` — SHA-256 `fe20d8f1b4cd18778002c6162de749b5250c760f8ad636d055682efe1172ebe4`;
- `GARDEN_CATALOGUE_v15.10.jsonl.gz` — SHA-256 `88c425ac3f547aae2461fda97109ba9dbde774fc59b57eead9f7a05ddb92f555`.

The r6 manifest records Technical+Catalogue graph reproduction PASS and byte-exact predecessor reconstruction PASS, but `semantic_admissions_recognized_by_build=false` and `predecessor_elision_allowed=false`. A proposed r7 text-source normalization was **not materialized as an admitted release**. The later small four-text reconstruction is not a lossless predecessor and is excluded from this binding. TASK-026 owns the remaining no-loss, directly-readable text-source normalization. Until TASK-026 passes, this binding supplies exact lineage identity but does not claim current-source normalization closure.


## Change in operating model

Garden upgrades should no longer depend on a human noticing each defect and issuing a separate prompt.

The AI owns routine specification closure. Humans remain necessary where Garden's protected constitutional process requires ratification or where a genuinely unresolved value/authority choice cannot be derived from existing admitted semantics.

## Objective

Given:
- the complete current Garden source;
- current DesignEpoch and dependency graph;
- protected constitutional intent/rights;
- evidence and implementation state;
- open findings and rejected alternatives;

the upgrade process repeatedly finds and resolves material gaps without requiring a new human prompt for each one.

## Closure loop

```text
RECONSTRUCT current system
 -> BUILD dependency/authority/effect map
 -> SEARCH for contradictions, omissions, stale assumptions and alternatives
 -> CLASSIFY materiality and owner
 -> GATHER missing evidence / run experiments / use tools
 -> GENERATE competing fixes including DO_NOTHING
 -> ATTACK each candidate
 -> VERIFY formal, empirical and implementation claims as applicable
 -> COMPARE whole-system consequences
 -> INTEGRATE best admissible candidate on a branch
 -> PROPAGATE to schemas, tests, registries, docs, code and dependencies
 -> RE-AUDIT whole affected closure and global invariants
 -> REPEAT until closure condition
```

Uncertainty is normally a work item, not a reason to hand the problem back to a human.

## AI-owned work

The AI should independently handle, where within existing authority:
- documentation inconsistencies;
- missing references/registrations/tests;
- duplicate or conflicting ownership;
- implementation defects;
- stale dependency bindings;
- schema/test propagation;
- alternative design generation;
- adversarial cases;
- literature/research comparison;
- simulations and executable checks;
- performance/complexity improvements;
- transition plans;
- whole-corpus retention checks.

It should infer cross-module consequences rather than wait for the user to name every affected subsystem.

## Escalation boundary

Escalate only when at least one of these remains after reasonable closure work:

1. a proposed change alters protected constitutional rights or foundational value commitments;
2. multiple admissible outcomes remain because a legitimate human/community preference is required;
3. a material authority claim cannot be resolved from available evidence/process;
4. applicable law/rights require a human or external institution to make the decision;
5. required independence cannot be obtained within the available system;
6. an irreversible/high-impact action requires ratification/authorization not already present;
7. a major architecture change changes Garden's constitutional meaning rather than implementation/representation.

"Human approval" is not an escape hatch for a failed hard gate. The human decision itself has only its applicable authority.

## Self-change rule

Garden may improve Garden, but consequential self-change cannot put sole proposer, implementer, verifier and authorizer control in one non-independent lineage.

The AI may:
- discover the gap;
- design the fix;
- implement the fix;
- generate proofs/tests/evidence.

Where independence is required, a separately qualified verifier/admission path must still evaluate the change.

AI authorship is neither a defect nor a certification.

## Better-than-Garden search

The process is allowed to discover an architecture better than the current Garden implementation.

It compares alternatives against Garden's protected objectives, rights, authority boundaries, evidence requirements and real-world outcomes. It must not preserve a current module merely because Garden historically contained it.

A change to protected objectives themselves follows the constitutional change path.

## Propagation rule

A material accepted candidate is incomplete until its dependency closure is propagated.

At minimum inspect:
- controlling definition;
- schemas/types;
- invariants;
- conformance/failure tests;
- function contracts;
- registries;
- authority/effect bindings;
- Book/human projection where relevant;
- implementation/prototypes;
- migration/compatibility;
- release manifest/DesignEpoch;
- rejected-alternative and audit records.

No "patch applied" claim before propagation closure.

## Closure condition

A version may reach upgrade closure only when:
- the audited scope is explicitly declared and the required systematic search/coverage pass has completed, so an empty finding list cannot masquerade as exhaustive review;
- no currently known material defect remains unresolved in the audited scope;
- all discovered material findings are FIXED, REJECTED_WITH_EVIDENCE, DEFERRED_WITH_OWNER/CONDITION, or ESCALATED under the explicit boundary above;
- affected tests/proofs/checks pass;
- retention/no-loss requirements pass;
- independent checks required by materiality pass;
- the system has been re-audited after the final material change.

Closure is not a claim that no future unknown problem can exist.

## Anti-stall and bounded-recursion rule

Finding another solvable material gap restarts the loop; it does not terminate the work with a report to the user.

Each upgrade cycle must also declare a bounded work scope, resource/review budget, checkpoint condition and stop condition. Materiality outranks raw finding count. Repeated low-value restatements, already-covered findings and changes whose expected value is below their verification/integration cost are rejected or deferred with a recorded reason and a concrete re-open trigger rather than causing infinite recursion.

If a required independent reviewer, tool, external institution or assurance dependency is temporarily unavailable, the AI may continue **noncanonical routine analysis and repair** that does not depend on that missing authority. It must preserve the blocked assurance state explicitly. Missing independent review cannot be relabeled as PASS, and protected admission/promotion remains blocked until the required independence is actually obtained.

The AI should report progress, but routine unresolved work remains its responsibility until fixed, rejected with evidence, deferred with an owner/trigger, proven blocked by an external dependency, or legitimately escalated under the escalation boundary.

## Upgrade work is not privileged

The goal of improving Garden does not authorize the means used to improve it. Research, data access, tool calls, experiments, code execution, reviewer invocation and any external effect remain subject to the same point-of-use authority, privacy, rights, law, safety and Human-Effect Closure rules as other actions. A useful upgrade objective cannot self-authorize intrusive evidence gathering or bypass external security.

Changes to a verifier, admission gate, protected policy, trust root or independence mechanism invalidate any qualification that depended on the prior version until the changed verifier/gate is independently requalified. The upgrader cannot modify the judge and then use the modified judge as independent proof of its own change.

## Executable closure reference

`prototype/upgrade_process.py` implements a narrow closure evaluator. It can return `CLOSE_CANDIDATE` only when audited scope and search coverage, material finding dispositions, bounded-cycle declaration, method authority, propagation, tests, retention/no-loss, verification independence, required independent review, protected authorization where applicable, and final re-audit are all resolved. `CLOSE_CANDIDATE` is not merge authority, canonical promotion, deployment certification or sovereignty.

## Core invariants

**AUP-001** Unknown != impossible; investigate before escalating.
**AUP-002** Gap discovery creates work, not automatic human delegation.
**AUP-003** Routine fixes propagate through the full dependency closure.
**AUP-004** DO_NOTHING remains a comparator.
**AUP-005** AI confidence does not substitute for evidence/proof.
**AUP-006** AI authorship does not create merge/admission authority.
**AUP-007** Required independent review cannot be simulated by correlated copies.
**AUP-008** Protected constitutional change follows the protected change path.
**AUP-009** Better architectures may replace current implementation when objectives/rights remain protected.
**AUP-010** Final re-audit occurs after the last material modification.
**AUP-011** Recursive upgrade work is bounded by declared scope/resources/checkpoints and cannot loop indefinitely on low-value findings.
**AUP-012** Missing required independence may block admission without blocking unrelated noncanonical repair work; blocked assurance can never be silently promoted to PASS.
**AUP-013** Upgrade objectives do not privilege upgrade methods; every consequential method remains independently effect-governed, and modifying a verifier invalidates dependent qualification until independent requalification.
