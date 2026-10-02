# Independent adversarial review

Status: IMPLEMENTATION. This review attacks the executable subset, not canonical Garden.

The native JSON-line gate suite executes 53 black-box cases against the compiled Rust process: 49 enforcement checks pass, zero fail, and four experiments document explicit trust limits. Legitimate scoped work writes a real sandbox file and returns an authenticated receipt; expected-denial cases are not the only positive controls.

Observed failures in earlier working revisions were retained in `attack-receipts-pre-repair.json` and `attack-receipts-state-flood.json`:

* Duplicate object keys used last-key-wins parsing. `{"operation":"execute","operation":"status"}` was accepted as status. Strict duplicate detection now rejects it at every nesting level.
* Reading a FIFO blocked the gate before the regular-file check. Nonblocking open and regular-file validation now return a bounded denial.
* Invented actors grew durable actor state despite lacking authority. Principal binding, unchanged registries for spoofed actors, and a global journal budget now bound this attack.
* Benign filenames with extensions failed because identifier validation excluded dots. Filename validation now admits ordinary extensions while rejecting traversal, leading dots, separators and special files.

Additional regressions cover exact malformed-wire hashes and explicitly truncated oversized-wire receipts, forged Unicode signatures, hard links, symlinks, delegation cycles and widening, receipt tampering at restart, interrupted-operation quarantine, consumed IDs/nonces, stale versions, revocation between evaluation and execution, proposal substitution, read-only scope, resource budgets and known-actor impersonation. Some of these repairs were discovered by the kernel/formal reviewers and independently exercised by this suite; the retained pre-repair runs do not claim all of them were independently observed to fail.

Four trust limits remain and are deliberately reported as LIMIT rather than PASS:

* Authenticated reviewers can report PASS for misleading content while omitting material facts. The gate verifies recorded review obligations; it does not solve general semantic truth.
* Distinct family/controller/lineage labels do not establish physical or epistemic independence. The harness intentionally creates all review records from one process and one representation, which the trusted registry admits.
* Supplied evidence bytes are now verified, durably content-addressed and rechecked before execution. Claimed origin and factual support still require semantic review. A supported registry record is not empirical proof.
* A hostile storage administrator can restore an older authentic state and matching journal, thereby rolling back a later revocation. The experiment performs this restoration without forging a signature. The agent API cannot access these files, but resistance to this expanded threat requires an external monotonic checkpoint; hash chaining alone does not establish freshness.

The Worker subset has a separate seven-case independent suite in `deploy/worker-site/tests/independent-attacks.test.mjs`. It exercises human/agent credential confusion, cross-session impersonation, attempted human-confirmation injection, concurrent receipt sequences, hostile stored-receipt corruption and strict JSON whitespace. All seven pass after repair. The deployment reviewer repaired stored-log signature/chain checks before mock file reads could launder a corrupted record, and corrected JavaScript's permissive Unicode whitespace parser. This Worker is EXPERIMENTAL and is not the native Rust gate.

Twelve additional integration cases in `run_http.py` launch the real HTTP controller and real gate subprocesses, then make loopback requests. All twelve pass: legitimate arithmetic/file work, missing session authority, unreviewed raw proposals, actor/admin injection, cross-session assessment reuse, consent/revocation, malformed bodies, cross-origin requests, resource rates and inert user HTML. Observations and full action receipts are in `http-attack-receipts.json`. Stored credentials are deliberately excluded from reports. This is local integration evidence; production proxy and browser-engine penetration are not claimed.

Declared limits: authenticated ingress and correct principal binding, trusted controller/OS isolation, signing-key secrecy and a finite test budget are assumed. The tests do not establish general cognitive independence, semantic omission completeness, correctness of all source evidence, full production container isolation or safety of arbitrary external tools. No real email, financial trading or other dangerous external effect was attempted.

Completion claim within this implemented, bounded surface: `NO_ADDITIONAL_MATERIAL_GAPS_DISCOVERED_WITHIN_DECLARED_SEARCH_SURFACE_AND_BUDGET`. The explicit trust limits remain unresolved for a broader autonomy level.
