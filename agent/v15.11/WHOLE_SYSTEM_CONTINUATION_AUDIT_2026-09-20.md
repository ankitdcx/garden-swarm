# Garden v15.10/v15.11 whole-system continuation audit — 2026-09-20

Status: NONCANONICAL ENGINEERING/AUDIT RECORD

## Scope
Continuation after the prior chat reached its context limit. This audit starts from current `main` after v15.11 integration PR #253 and the later operational cleanup commits.

## Confirmed durable state
- v15.11 compact integration is merged.
- v15.11 keeps separate Book, Technical review projection, Catalogue review core, History, retention ledger, package-binding manifests/receipts, executable runtime/transition/upgrade references and tests.
- v15.11 remains a noncanonical working candidate.
- Independent high-risk external review is not PASS.
- OpenRouter review remains paused/blocked; do not spend or silently substitute reviewers.

## Audit finding A-01 — stale full-Catalogue binding in review core
The Catalogue review core still named an earlier generated full Catalogue:
- stale SHA-256: `afc8ae281f67bd30f5f1648e1b37980c89739baa583e23427a39fc79e631d5ca`
- stale size: 3,555,977 bytes

The final v15.11 retention ledger, release manifest and closure receipt consistently bind:
- SHA-256: `d02dad9662bedb9d9253ed9eaabc6ec0462ee67697c29201d85b01323fb97f8c`
- size: 4,899,658 bytes

Disposition: FIXED on this branch by updating the review-core boundary to the final bound artifact.

## Audit finding A-02 — durable source materialization gap
The repository stores compact review projections and hash-binding evidence, but does not store the final full standalone v15.10/v15.11 primary-source bytes or ZIP packages. The ledger explicitly records that the full standalone Catalogue is not committed.

This is not semantic loss by itself, but it means the repository cannot independently reconstruct the claimed standalone package from repository bytes alone. A hash/URI binding proves identity only if the bound bytes remain durably retrievable.

Disposition: OPEN. Do not mark repository-only standalone reproducibility PASS until the exact bound primary bytes/package are durably materialized in an approved artifact store or repository mechanism and reverified by SHA-256.

## Audit finding A-03 — independent review remains blocked
Issue #259 records no successful external inference for the current cycle. The required reviewer slot had no eligible endpoint under the then-active constraints.

Disposition: OPEN / NON-BLOCKING FOR NONCANONICAL REPAIR / BLOCKING FOR ANY CLAIM THAT REQUIRES INDEPENDENT HIGH-RISK REVIEW.

## Audit finding A-04 — status separation remains correct
Current files continue to distinguish source retention, executable-reference tests, formal proof/certification, and canonical admission.

Disposition: PASS for this audit scope.

## Next closure order
1. Merge A-01 repair after CI.
2. Materialize exact final v15.10 and v15.11 standalone primary bytes/package durably, then verify all recorded hashes.
3. Run repository/package closure verification against those bytes.
4. Resume independent review only after explicit budget authorization and eligible governed reviewer routing; no silent reviewer substitution.
5. Re-audit after the last material change.


## Continuation finding A-05 — standalone materialization branch is structurally incomplete
Audit of PR #271 at head 4af8f81dc3467526611c4ddfbab27a5b146f93bd found that its readable-text manifest declares v15.11 Technical reconstruction from five parts, intentionally reusing v15.10 part02. That reuse is explicit and therefore not itself a loss defect.

However, the content directory currently contains only manifests; the large content objects promised by the PR description are not materialized at this head. The import inbox also contains only README.md. Public-release integrity CI fails at this head.

Disposition: OPEN / BLOCKS MERGE OF #271 AS A COMPLETED MATERIALIZATION CLAIM. Preserve the branch; finish exact payload import or use another deterministic source that reproduces all recorded hashes before merge.

## OpenRouter authorization update
The user explicitly reauthorized cheap OpenRouter queries on 2026-09-20 for whole-document verification and confirmation that nothing useful is lost from Garden 15.x. Existing per-call/task/provider/privacy controls remain applicable. External model output is challenger evidence, not semantic or canonical authority.

Do not treat the historical run-259 DeepSeek-slot failure as a reason to weaken its recorded protocol. A new retention-focused review packet may use currently eligible cheap models under the authorized budget, with model identity and source binding recorded.
