# Branch cleanup — 15 September 2026

The user paused the Coordinator because of repeated request-limit errors and explicitly requested cleanup of all old branches. Keep all automated provider work paused until the user resumes it.

This archive preserves exact changed-file bytes from retiring branches, under inert .snapshot filenames. It does not install their workflows, revive Process v2, admit their deltas, qualify old packets, or lift freezes. The manifest binds original paths, branch heads and Git blob hashes. Source commits retain full-tree lineage.

- `ip/final-origin-backfill-data-20260915`: PENDING_INDEPENDENT_REVIEW; 3 preserved files.
- `ip/public-patent-provenance-current-main-20260915`: MERGED_PR_169; 1 preserved files.
- `ip/public-patent-provenance-current-v2-20260915`: SUPERSEDED_BY_PR_169; 1 preserved files.
- `process-v2-algebra-binding-20260915`: RETIRED_SUPERSEDED_PROCESS; 14 preserved files.
- `process-v2-governed-20260915`: RETIRED_SUPERSEDED_PROCESS; 1 preserved files.
- `repair/project-audit-scheduler-cost-20260915`: ALREADY_MERGED; 0 preserved files.

## Pending work preserved

- PR #169 provenance notice merged as `0075300a863be901e30351d85eb372818e159b26` after its three successful checks. No new legal status is asserted.
- PR #151 origin inventory: failed independent review; preserve all bytes for later review rather than publishing it as an accepted root inventory.
- Superseded Process-v2 branch stays retired; compatible implementation salvage belongs to #148 under admitted Process 1.4.
- Rate-limit recovery and qualified-review progress: #138/#114/#113/#148. Paid global durable reservations remain #75.
- Nightly review #115 is a due Coordinator obligation, not another timer. Research findings #140 require triage and evidence-backed closure; publishing a finding does not close it.


Deletion is a separate operation after this archive is merged. Branch names must still match the recorded SHA; moved or protected branches and branches with open PRs must be retained. No paid model calls are required for cleanup.

Snapshot payloads are intentionally opaque historical records. The ordinary current-repository reference scanner does not certify their internal links; use their exact source URLs and blob manifest for reconstruction. No current-source reference rule is weakened.
