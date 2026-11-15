# Versioned evaluation and reliability extensions

Run `python p4_regression.py --output regression.json`.
The committed `tests/fixtures/p4-regression-v1.json` freezes the existing ten
context cases and expected outputs as a separately versioned dataset.
The runner calls existing `run_context` and `grade` implementations.

It checks authorized outputs, missing/restricted/sensitive/conflicting evidence,
context bounds, hostile embedded instructions and unauthorized plans. Reports
include traces, tool counts, retry delays, case-level failures, source/dataset
hashes and median/nearest-rank p95 local latency. A failing case exits 1.
Tests deliberately replace the action with quarantine to prove the gate rejects
a broken candidate. Source hashes support change review; they are not signed
supply-chain attestations.

This is a development regression set, not newly held-out data. No model is
called; model cost/tokens remain null. Existing live comparison and human review
commands remain unchanged, and the AI-quality decision stays blocked.
The previous inline CI still runs baseline, orchestration, resilience, context,
observability, review and fallback checks.

The customer-deployment rehearsal combines these checks with actual local
Control Tower transitions, evidence verification and backup/restore. It does not
turn the Project 4 reference runner into a live planning agent.
