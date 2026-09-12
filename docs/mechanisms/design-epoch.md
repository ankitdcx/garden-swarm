---
title: DesignEpoch Invalidation
---

# DesignEpoch and Dependency-Aware Invalidation

**Problem:** a proof, cache, summary, policy, or generated artifact can remain syntactically valid after a source assumption or semantic dependency changes.

**Garden claim:** derived artifacts remain bound to the DesignEpoch and relevant dependencies under which they were admitted. A relevant change makes them `STALE`, `UNKNOWN`, or otherwise revalidation-required rather than silently reusable.

## Executable reference

See `prototype/design_epoch.py`.

A minimal binding contains:

```text
artifact_id
DesignEpoch
dependency -> version map
```

Validation compares the binding with the current epoch/dependency state and returns:

```text
CURRENT | STALE | UNKNOWN
```

## Attack it

Try a flattened natural-language summary that drops lineage, a cached policy after a consent-definition change, an omitted dependency, or a proof whose premise changed without explicit invalidation.

See `ATTACK_SURFACE.md`.

## Important limit

Hash/version binding catches declared dependencies. It does not magically discover every semantic dependency. That remains an implementation and assurance problem to test explicitly.
