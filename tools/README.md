# Garden review tools

These tools are bounded public-source review utilities. They do not have canonical-promotion, merge, deployment or private-source authority.

## Gemini pair

- `gemini_free_review.py` performs the direct Google Gemini Developer API review and writes a proposal-only `gemini-review.json` receipt.
- `run_gemini_free_review.py` is only the quota-preserving scheduler/wrapper. It either invokes `gemini_free_review.py` on the configured cadence or writes an explicit `SKIPPED_FREE_QUOTA_PRESERVATION` availability receipt.

The two files are intentionally separate so provider logic and quota policy can evolve independently. The wrapper must never be interpreted as a second independent Gemini reviewer.

## Free-model rotation

OpenRouter free routes are selected dynamically and are bounded separately from the Garden semantic-admission quorum. One free model call in a run is reviewer evidence, not sufficient independent review for semantic admission.

Generated selections and receipts belong under ignored runtime/outbox paths and are uploaded as CI artifacts rather than committed as Garden source.
