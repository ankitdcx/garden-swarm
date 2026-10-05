# Garden Model Capability Lab

**Status:** active development; noncanonical measurement evidence only.

## Purpose
Compare model families on fresh reasoning tasks without granting model authority, Proof, or Garden semantic status.

## Protocol
The lab has two complementary rounds.

### A. Common seeded sentinel
A fresh run seed deterministically generates 10 tool-free reasoning tasks with locally computed answer keys. Every model gets the identical prompt. Exact scoring, model identity, latency, cost, failures, and response hashes are retained.

### B. Reciprocal challenge tournament
Each participating model independently authors 10 novel reasoning questions designed to discriminate frontier reasoning. It must freeze for each question: prompt, answer, scoring rule, ambiguity notes, and difficulty claim **before seeing any peer answer**.

Admission rejects questions that require private knowledge, current web facts, tools, subjective taste, model identity, or unverifiable grading. Deterministic/verifiable questions are preferred.

Every model then answers every other model's admitted questions under the same no-tools conditions. A model does not receive its own answer key while solving.

After deterministic scoring, all participating judges independently receive anonymized questions, frozen keys, answers and machine scores. They may challenge an answer key or score with a concrete counterexample. Peer majority is never Proof.

## Final rating
Publish common-sentinel score, reciprocal solve score, authoring quality, calibration/invalid-output rate, cost, latency and per-category results. Publish a consensus score only where independent judges converge and no reproducible counterexample remains; otherwise preserve DISPUTED/UNKNOWN.

A final rating must not erase disagreement. One valid counterexample overrides any number of agreeing judges.

## Boundaries
Benchmark rank cannot select Garden authority, admit a semantic change, certify AGI, or prove general intelligence. A 10-question round is a sentinel; stronger claims require multiple fresh rounds and uncertainty intervals.
