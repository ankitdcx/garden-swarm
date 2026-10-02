# Candidate improvements — no canonical promotion

**Status: CANDIDATE / NO EXECUTION AUTHORITY.** This document proposes changes;
it changes no canonical text, policy, trust root or runtime permissions. Agents
cannot apply these proposals to their own policy, verifier, or authority state.
Any later implementation requires the externally governed approvals stated below.

Basis: the independently frozen design and final source comparison in
[blank-slate.md](blank-slate.md), the bounded-model evidence in
[formal-verification.json](formal-verification.json), and separately authored
black-box [native attack traces](../gardenbench/attack-receipts.json). The final
native suite records 49 PASS, zero FAIL and four LIMIT observations against
release SHA-256 `4bc6ceaba7d2ea5bc274039fb98f6816d265cd5f0548aca71d698c158666577a`.
Separate reasoning/fixtures do not establish independent model-family assurance;
the reviewers share a family unless authenticated provenance establishes otherwise.

| Observed LIMIT fixture | Remaining boundary |
|---|---|
| `authenticated_storage_rollback_limit` | Restoring authentic state and journal can undo revocation. |
| `declared_independence_trust_limit` | Distinct registry labels do not prove independent reviewers or representations. |
| `evidence_semantics_trust_limit` | Content hashes do not prove source origin or factual support. |
| `semantic_review_trust_limit` | Authenticated PASS can still admit misleading or omitted material content. |

Each fixture is a `results[id=…]` entry in the native traces; its replay code is in
[gardenbench/run.py](../gardenbench/run.py). Source identifiers below refer to
[source-map.json](source-map.json); a canonical source rule does not make this
proposed mechanism canonical.

## CDELTA-01 — External monotonic checkpoint (priority 1)

**Diff scope:** add a protected external monotonic authority/receipt checkpoint,
startup comparison and single-writer compare-and-swap protocol. Anchor revocations
and consumed request identities before acknowledging control changes or admitting
effects. A periodic asynchronous log hash leaves an unprotected rollback window.
Restart, forked writers, unavailable anchors or mismatches must deny effects.

**Source/status:** CANDIDATE mechanism supporting canonical `AGT-017`, `EXE-002`,
`DEPOCH-010` and `VER-003`; no canonical amendment proposed.

**QSE:** missing question—who controls the anchor; variable—commit order;
representation—freshness versus integrity; omission—revocations and spent IDs;
boundary—snapshot restoration; rule-conformant attack—restore valid signatures;
redesign—external transactional registry; integration—crash between local/anchor
writes.

**Attack/regression:** retain `authenticated_storage_rollback_limit` and
`replay_after_restart`; add stale checkpoint, fork, anchor outage and crash-order
regressions before claiming rollback resistance.

**Required approval:** legitimate scoped trust-root administrators plus an
independent security/operations reviewer must approve anchor ownership, protocol,
recovery and key rotation. **Residuals:** anchor compromise, distributed consensus,
availability and adapter-specific exactly-once effects remain separate problems.

## CDELTA-02 — Authenticated verifier independence and HC identity (priority 2)

**Diff scope:** replace structural role labels with authenticated, revocable
identity/grant records. Bind HC identities used for human authority/consent to the
actual principal, affected scope, policy epoch and approval receipt. Bind reviewers
to authenticated control/model/prompt/tool/evidence/representation provenance;
check both proposer-reviewer and required reviewer-reviewer independence. Unknown
or overlapping required domains remain non-PASS.

**Source/status:** CANDIDATE mechanism supporting canonical `K-INT-006`,
`K-INT-013`, `EVIDENCE-OVERLAP`, and candidate `HUMAN-EFFECT-CLOSURE`/
`REP-002-006-008`. No identity acronym or role label establishes human legitimacy.

**QSE:** question—who can attest independence; variable—controller/lineage;
representation—human versus service identity; omission—shared sources;
boundary—credential compromise; compliant attack—distinct labels, one controller;
redesign—external institutional attestations; integration—identity revocation.

**Attack/regression:** retain `declared_independence_trust_limit`, `shared_family`,
`shared_controller`, `self_certification` and `bound_actor_identity_spoof`; add
cross-reviewer overlap and stale human-consent credentials.

**Required approval:** relevant human authority holders and independently
administered identity/security reviewers must approve the trust registry and
independence profile. **Residuals:** authenticated identity does not prove consent,
legitimacy, truth, noncollusion or genuinely different internal representations.

## CDELTA-03 — Evidence source provenance (priority 3)

**Diff scope:** extend evidence records with authenticated acquisition receipts
binding source identity, retrieval time, exact content hash, transformations and
claim-support method. Preserve conflicts and source lineage through summaries;
reject absent/stale provenance or unsupported claim links. Keep content storage
and semantic support as separate predicates.

**Source/status:** CANDIDATE mechanism supporting canonical `K-INT-001`,
`K-INT-007`, `K-INT-015` and `RESULT-ALG-002`.

**QSE:** question—was the source actually consulted; variable—freshness;
representation—bytes versus claim; omission—transformations; boundary—source
spoofing; compliant attack—real hash, invented origin; redesign—signed acquisition;
integration—retrieval credentials and content-addressed storage.

**Attack/regression:** retain `evidence_semantics_trust_limit`,
`evidence_blob_registration_integrity` and `evidence_blob_tamper_before_execution`;
add forged acquisition, stale origin, conflicting sources and laundering through
summaries.

**Required approval:** scoped evidence/data owners and independent provenance
reviewers approve accepted sources, acquisition methods and privacy constraints.
**Residuals:** authentic sources can be false; independent empirical support and
domain-specific relevance cannot be inferred from signatures or source count.

## CDELTA-04 — Bounded strategic truthfulness review (priority 4)

**Diff scope:** add a versioned decision record containing applicable alternatives,
no-action, affected people, evidence/uncertainty, assumptions, rejected options and
decision-relevant omissions. Deterministically check completeness within a finite
profile; independently assess material support/omissions. Do not authorize an
effect merely because the record is syntactically complete or critics agree.

**Source/status:** CANDIDATE mechanism based on user-bound implementation
`MISSION-QSE`/`MISSION-STRATEGIC-TRUTHFULNESS`, canonical `K-INT-002`/
`ACT-006`, and candidate `REP-002-006-008`; not a general truthfulness theorem.

**QSE:** question—whose options disappeared; variable—materiality; representation—
effects versus persuasive prose; omission—counterevidence; boundary—critic capture;
compliant attack—literal truths that steer the decision; redesign—bounded domain
comparators; integration—shared context causing collective omission.

**Attack/regression:** retain `semantic_review_trust_limit`,
`reported_material_omission`, `reported_qse_finding` and `suppress_human_effect`;
add selectively true statements, hidden alternatives and mutually correlated
critics against externally specified materiality cases.

**Required approval:** affected-domain owners and suitably independent semantic
reviewers approve the finite profile and applicability rules. **Residuals:** open
world truth, relevance, collective omission and novel harms remain unresolved;
unsupported consequential conclusions must continue to deny or defer.

## CDELTA-05 — Externally governed control updates (priority 5)

**Diff scope:** retain the absence of an agent policy-update operation. Future
updates use a separate externally authorized transition package binding old/new
policy hashes, epoch, identity/grant changes, control obligations, approval and
rollback-safe migration. Split credentials for evidence registration, assessment
registration, revocation and trust-root migration; a generic control token is not
semantic authority. Model replacement receives no inherited grants.

**Source/status:** CANDIDATE mechanism supporting canonical `AGT-016`, `VER-003`,
`SEC-LEARN-003`, `ACT-003` and candidate `RCC-CONTROL-CLOSURE`.

**QSE:** question—who may approve this scope; variable—epoch/dependency closure;
representation—capability versus authority; omission—key/monitor changes;
boundary—control compromise; compliant attack—authorized token, unauthorized
scope; redesign—signed external migration ceremony; integration—stale grants,
checkpoint and binary/adapter versions.

**Attack/regression:** retain `modify_gate`, `forged_control_credential`,
`stale_policy_version`, `successor_inherits_authority` and the bounded model's
version/epoch/successor negative controls; add unauthorized signer, partial
migration, rollback and protected-floor removal cases.

**Required approval:** actual scoped authority holders, affected obligation
owners and an independently protected verifier approve each exact transition;
canonical changes require their own established governance process. No agent,
model critic, operator label or this document can self-authorize that process.
**Residuals:** corrupt legitimate approvers, inadequate profiles, host compromise
and migration recovery remain explicit trust limits.

These deltas are review proposals, not completed controls. Promotion requires
implemented scoped diffs, replayed regressions, honest residuals and the relevant
external approval; the finite model and test receipts confer no authority.
