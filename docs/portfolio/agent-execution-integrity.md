# Agent Execution Integrity & Workflow Safety Lab

**Status:** Synthetic local implementation and scripted benchmark only; not a deployed agent executor, production IAM control, external model robustness study, or independent security assessment.

## Purpose and code reuse

This extends the existing bounded review-ticket project **without changing its established local-ticket workflow or release decision**. The existing `app/workflow.py:digest` canonical JSON digest is reused, and the separation of requester/approver/executor roles follows `tower/access_demo.py`. The newer `app/execution_integrity.py` is an **independent defensive gate / companion**: it is not automatically wired into `app/agent.py` or live AWS Bedrock tool invocations. Integrating it into a deployed dispatcher remains a future work item.

Related work is deliberately not duplicated: [FedRAMP Continuous Monitoring](https://github.com/SushiBear21/agentic-security-workflow/issues/22), [Agent Identity Governance](https://github.com/SushiBear21/agentic-security-workflow/issues/21) and the [synthetic AI governance / MCP identity work](https://github.com/SushiBear21/agentic-security-workflow/pull/27). The companion does not claim those PRs have been merged or independently verified.

## Enforcement boundaries

1. **Provenance**: host-supplied manifest pins each source's document ID, URI, audience, and exact text digest. The returned content remains `evidence_only`: it is never authorized policy.
2. **Order**: `INIT → OBSERVED → VALIDATED → PROPOSED → APPROVED → EXECUTED`. A host-owned precondition can deny hazardous operations before proposal.
3. **Exact action**: tool name, tenant, scoped synthetic ticket resource, and tool arguments are checked against fixed host policy.
4. **Independent human-role emulation**: only the host-designated lab approver can issue an HMAC-signed approval after reviewing the exact proposal. **No actual person approved the benchmark cases**; the harness simulates that role.
5. **One-time execution**: signed claims bind exact action digest, evidence reference, tool and policy versions, tenant, executor, generation, issue/expiry time, and a random nonce. The gate consumes nonce before writing a mock effect. RLock protects concurrent calls within the process.
6. **Context and rollback**: model summaries are data, never approval records. Rollback increments a host-owned generation and invalidates pending approvals. A model-supplied summary cannot restore the authorization ledger.
7. **Audit**: each checked operation's allow/deny decision is recorded with actor, versions, generation, and digest. It contains no HMAC key.

This is a **mock local executor**. Do not extrapolate it to AWS IAM, tool-side supply-chain compromise, independent approver authentication, distributed exactly-once semantics, or immutable storage.

## Reproduce: no AWS account or paid model required

```bash
python -m unittest tests.test_execution_integrity -v
python -m tower.integrity_benchmark --output integrity-benchmark.json
```

The benchmark builds **80 fixtures**, with six adversarial families × 10 cases = 60, plus 20 clean controls; three repeated trials in two configurations give **480 deterministic mock executions**. For each run the JSON records encounter status, reason for denial, authorization audit events, and actual mock state-changing effects.

The comparator `prompt_only_emulated` is a deliberately unguarded scripted model **with zero LLM API calls**, not measured susceptibility of a real prompt-only LLM. Its failures are by construction and must **not** be presented as empirical prompt-injection success rates. The defended condition calls the deterministic gate for each run. This benchmark does not measure statistical model variation, human review quality, adversarial prompt discovery, latency, or live network egress.

### Local observations (2026-11-23)

| Measurement | Scripted comparator | Deterministic gate |
|---|---:|---:|
| Executions | 240 | 240 |
| Adversarial challenge runs | 180 | 180 |
| Encountered challenges | 180 | 180 |
| Unauthorized mock side effects | 180 (by design) | **0** |
| Challenge attempts blocked | 0 (by design) | **180** |
| Clean task completion | 60/60 | **60/60** |
| Complete per-run audit records | 0/240 (no gateway) | **240/240** |

The local `unittest` run passed **13/13** tests, including a sixteen-way concurrent replay test. Acceptance targets for this synthetic gate were met: 0/180 unauthorized defended effects, at least 57/60 clean runs, and 100% audit coverage. **Those are local observations only until CI is checked independently.** Zero observed failures in designed fixtures is not proof of agent security.

### Threat families

- Retrieved document text does not match trusted ingestion hash.
- MCP-style tool metadata claims authority that its source does not have.
- Agent tries to propose before required environment validation.
- Exact approved payload is mutated before execution.
- A prompt summary attempts to retain approval after rollback.
- A legitimate user requests an action while an operational dependency is still active.

## Integration and remaining gaps

The RAG repository has a separate **opt-in** trusted ingestion manifest check in `app/evidence_provenance.py` and `app/rag_service.py`. That protects retrieved evidence only when an administrator configures `RAG_PROVENANCE_MANIFEST_PATH`. It does not grant policy authority to document text.

Follow-on engineering should include authenticated independent approvers, durable atomic nonce/side-effect state across crashes and multiple workers, canonical tool-image digests and supply-chain attestation, state-transfer audit protection, actual MCP calls, real sandbox/egress controls, realistic model-driven attacks, true no-gateway LLM runs, third-party adversarial assessment, and latency budgets. There are no cloud deployments or live data changes in this lab.

**Evidence discipline:** This artifact is a personal defensive exercise, not commercial compliance ownership, FedRAMP authorization, production SOC operations, or verified external compromise resistance.
