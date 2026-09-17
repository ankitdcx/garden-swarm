# v15.9 review campaign — bounded restart

The user explicitly authorized proceeding despite the abandoned historical Qwen
call's billing uncertainty, and up to US$10 total for the v15.9 document review on
2026-09-17. This is a non-renewing campaign authorization, not $10 every day.

The trusted campaign policy binds the exact supplied v15.8 master hash. A review
directive must select that campaign and its extracted target must trace to that
exact source or a byte-hashed source slice registered against that master in the
trusted policy. The directive cannot change the campaign's source or budget.

One exact historical attempt is eligible for a financial-risk exception. Its full
record hash, run ID, model and abandoned administrative status must match. Its
original UNKNOWN status and null actual cost remain unchanged. Its full $0.05
reservation is counted as an accounting allowance, not reported as a known bill.
It is never retried or admitted as review evidence. Any modified, additional or
in-flight unresolved attempt retains the ordinary blocking behavior.

All ledger costs plus that allowance count against the total ceiling. A new date,
target, packet, cycle or reviewer does not reset it. The existing live provider
usage, credit, per-call reservation, sequential dispatch, independent branch and
protected source checks still apply. Live usage is conservatively included in the
funding check, so available spending can be below the nominal $10 ceiling.

This explicit campaign exception supersedes the generic unknown-billing stop only
for the exact authorized historical record. It does not reinterpret the generic
rule or authorize future exceptions. Removing the campaign policy disables the
exception; it does not erase the old record.

## Run readiness

The first public design excerpt, U15.8-1 Human-Effect Closure, is staged under
`review-inputs/v159/`. It is an exact slice of the supplied master, with its line
range and hashes in the trusted policy. The launch directive includes exact
cross-layer candidate passages, verified inherited context, an omission ledger,
and a hash commitment to an independently written ChatGPT assessment. Baseline
text is withheld from the initial reviewers.

The directive must also be staged in persistent review state. On a matching
material source event, continuation validates the exact source, packet, capsule,
model-family order, neutral query, baseline commitment and explicit launch flag
before dispatching one isolated BLIND review. A source push without that matching
directive still cannot start inference. The worker repeats validation and live
funding checks before its reservation and call. The ordinary completion path can
then advance the other three isolated reviewers. Reconciliation still requires
ChatGPT's next explicit phase directive.

The current four model slots remain unchanged. The user permits Gemini if needed,
but a replacement must be explicit, use a new convergence cycle, and preserve four
independent reviewer families. No unverified Gemini model ID is introduced here.

Canonical Garden v15.5 source, authority and certification are unaffected. The
v15.8 attachment remains a working candidate; this runner repair is not v15.9.
