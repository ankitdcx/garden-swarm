---
title: Authority Composition
---

# Authority Composition Without Amplification

**Problem:** individually compliant agents can form a chain whose combined effect exceeds the authority any participant should be able to create.

**Garden claim:** delegation/composition may narrow authority but cannot silently expand it.

A useful conservative model is:

```text
EffectiveAuthority(A -> B -> C)
  subset_of Authority(A) ∩ Authority(B) ∩ Authority(C)
```

This is an explanatory model, not a replacement for the richer canonical capability/envelope/policy semantics.

## Executable reference

See `prototype/authority.py`.

The regression suite includes an A -> B -> C case where:

- A may suggest;
- B may use a low-impact tool;
- C may execute a high-impact action;
- the composed path is rejected because `execute_high` is absent from the common authority intersection.

## Attack it

Try split-action recombination, quorum authority laundering, parent-budget resets, parallel child amplification, or confused-deputy routing.

See `ATTACK_SURFACE.md`.
