# Test ownership

Garden uses distinct test classes rather than one undifferentiated test tree.

- `prototype/tests/` — FunctionContract and reference-semantic conformance for `prototype/`.
- `server/tests/` — discovery/MCP service contract, envelope, transport-security, and integration tests.
- `swarm/tests/` — orchestration/synthesis contract tests.
- `tests/adversarial/` — mechanism falsification and attack-surface regression tests. These do not establish FunctionContract conformance by themselves.

CI aggregation rule: a repository-level PASS requires every applicable test class and every applicable GSL conformance stage to PASS. A PASS in one test root cannot override FAIL/UNKNOWN/STALE/INCONCLUSIVE in another.
