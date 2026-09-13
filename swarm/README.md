# Garden Swarm Orchestrator — scaffold v0.1

Purpose: heterogeneous, reproducible adversarial review of the frozen Garden v15.5 five-file source.

Design rules:
- dry-run is the default;
- live provider calls require an explicit `--live`;
- `OPENROUTER_API_KEY` is read only from the environment;
- the key is never written to receipts;
- OpenRouter requests enforce ZDR where supported;
- source files are hashed before review;
- model outputs are proposals, not accepted Garden changes;
- disagreements and blockers are preserved rather than majority-voted away;
- any possible gap that may be covered elsewhere must be marked for cross-reference checking.

Initial calibration uses a small heterogeneous panel. After calibration, increase role count and section coverage.

## Dry run

From the repository root:

```bash
python swarm/orchestrator.py
```

This creates `swarm/runs/latest-plan.json` and spends no model credit.

## Small live calibration

Only after OpenRouter credit is available:

```bash
python swarm/orchestrator.py --live --max-calls 4
```

The first live run should stay small. Review the receipts before scaling.

## Full design

The long-term pipeline is:

frozen v15.5 -> semantic work packages -> heterogeneous reviewers -> fresh-source research ->
cross-reference check -> adversarial challenge -> synthesis -> GSL-COMPARE/DO_NOTHING ->
invariants/tests -> candidate successor

The scaffold is intentionally not an autonomous merge/deployment system.
