# Project 4 — AI Governance and Evidence Matrix

## Scope and ownership

The portfolio author owns the evaluation dataset, implementation,
human review, documentation, and laboratory readiness decision.

The system evaluates synthetic asset-review drafts.
It does not execute remediation or create production tickets.

Human review is performed by the portfolio author.
Independent review and separation of duties are production
recommendations, not implemented controls in this exercise.

## Evidence register

| Evidence | Location | What it establishes |
| --- | --- | --- |
| Baseline and negative control | p4_baseline.py; lesson 1 reports | Structured checks detect deliberately incorrect responses |
| Bounded orchestration | p4_orchestration.py; lesson 2 results | Entire tool plan is checked before dispatch |
| Reliability | p4_reliability.py; lesson 3 results | Synthetic failure classification, shared attempt limits, and in-memory idempotency |
| Context boundaries | p4_context.py; lesson 4 results | Relevant context selection, conflict handling, size limits, and fixture-based access restrictions |
| Live comparison | docs/p4-lesson5-results.md; retained comparison.json | Two configurations, three repeats, 24 model calls, latency, tokens, and estimated cost |
| CI evidence | docs/p4-lesson6-results.md; downloaded CI artifact | Reproducible offline checks, negative control, source hashes, and report hashes |
| Human evaluation | docs/p4-lesson7-results.md; retained human-review.json | Actual human judgments linked to the evaluated report |

## NIST AI RMF 1.0 mapping

| Function | Lab implementation | Evidence | Limitation |
| --- | --- | --- | --- |
| GOVERN | Named owner, explicit review rubric, documented boundaries | This matrix; human-review.json | Single-person review; no independent enterprise approval |
| MAP | Intended use and synthetic failure scenarios defined | Evaluation cases and lesson results | Small development dataset; no representative enterprise traffic |
| MEASURE | Contract checks, live repetitions, latency, tokens, estimated cost, and human review | comparison.json; session 7 results | Small sample; no statistical superiority or zero-hallucination claim |
| MANAGE | Invalid outputs rejected; initial schema failures investigated; prompt corrected and reevaluated | Preserved failed smoke report and successful subsequent reports | Operational readiness decision remains for session 8 |

## OWASP LLM Top 10 — 2025 edition

The year is part of every identifier below.

| Risk | Implemented mechanism | Evidence | Remaining gap |
| --- | --- | --- | --- |
| LLM01:2025 Prompt Injection | Untrusted document text separated from instructions; fixed permitted action; structural validation | Injected-context case and reviewed live responses | One synthetic probe does not establish comprehensive injection resistance |
| LLM02:2025 Sensitive Information Disclosure | Sensitive fixtures blocked before inference; restricted context excluded | Sensitive/restricted cases; zero model calls for blocked cases | Labels are trusted fixtures; no authenticated retrieval or general DLP |
| LLM05:2025 Improper Output Handling | Strict JSON parsing, field checks, fact/citation checks, rejection of malformed output | Initial schema failures; parser tests; successful schema-prompt correction | No production downstream integration tested |
| LLM06:2025 Excessive Agency | Retrieval-only tool plan; whole-plan authorization; bounded attempts; no model action tools | Unauthorized-plan tests and traces | Model-generated planning and production permissions remain outside scope |
| LLM09:2025 Misinformation | Structured fact checks plus human review of narrative claims | Session 7 judgments and rationales | Human review is limited to this small sample |
| LLM10:2025 Unbounded Consumption | Three-attempt synthetic tool budget; 24-call live-run ceiling; 512 output tokens per call; soft cost stop | Source code, budget tests, comparison report | Soft budget can overshoot one call; provider timeout may still incur charges |

## Selected NIST SP 800-53 Rev. 5 concepts

These are partial lab analogies, not assertions that the complete
controls are implemented or assessed.

| Control | Lab evidence | Implementation boundary |
| --- | --- | --- |
| AC-3 — Access Enforcement | Audience-based fixture filtering and tool allowlist | No authenticated user identity or production authorization service |
| AU-3 — Content of Audit Records | UTC timestamps, case/configuration/repeat, traces, request IDs, and hashes | Editable local evidence; no immutable or signed audit store |
| CM-3 — Configuration Change Control | Versioned branch, Git commits, CI checks, documented prompt correction | Protected branches and independent approval are not established here |
| CA-7 — Continuous Monitoring | Automated offline checks on repository changes | No continuous production model-quality monitoring |
| IR-4 — Incident Handling | Recorded schema failure, diagnosis, correction, and validation | Development failure-handling example, not a production incident-response capability |

## Open risks

| Risk | Status | Owner | Future treatment |
| --- | --- | --- | --- |
| Small dataset was used to improve the prompt | Open | Portfolio author | Add a larger independently held-out evaluation set |
| Audience and sensitivity labels are synthetic | Open | Portfolio author | Integrate authenticated authorization and data-classification controls before production use |
| One person implements and reviews the system | Open | Portfolio author | Add independent review and enterprise decision rights |
| Reports and reviews are editable | Open | Portfolio author | Add signed or immutable evidence where required |
| Provider behavior may change | Open | Portfolio author | Define live reevaluation triggers for model or prompt changes |
| Idempotency fixture is not durable or concurrent | Open | Portfolio author | Validate persistent storage and crash/concurrency behavior before integration |

## Interpretation

Passing contract checks and human review provides evidence for this
laboratory dataset and configuration.

It does not establish NIST compliance, a federal authorization,
production readiness, statistically superior model performance,
or general resistance to prompt injection.

The dataset is a development regression set used during prompt
improvement. It is not an independently held-out benchmark.

Final configuration selection and operational readiness remain
for session 8.

## Primary references

- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [OWASP LLM Top 10 2025](https://genai.owasp.org/llm-top-10/)
- [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)