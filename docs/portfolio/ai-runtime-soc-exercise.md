# AI runtime SOC integration exercise (#32)

Synthetic-only. This is an offline, local SIEM-equivalent adapter, not a production SOC, real DLP, independent human approval, or external EDR/SOAR integration.

## Reuse / coordination
- Stacked on PR #27 at 7f29a781aad203797888803a95fe0065729b9e33; actual MCP audit receipts and exact-request single-use approval are reused. No changes to the PR #27 or #31 implementation files.
- PR #31 at 75cc1736e261008438b682f562f153c5217cafc1 provides the integrity audit contract. The adapter currently uses a scripted contract fixture; fresh integration with its unmerged implementation remains pending.
- #18's endpoint workbench (aws-security-response-lab PR #2 at 7018def69bf97feda639e76cfc880e4f92f8b0f0) informs the duplicate-safe case and maker/checker pattern. This is a distinct local AI event route, not a cross-repository live EDR integration or closure of #18.
- Secure Enterprise RAG has a monitored handler and injection fixtures. No live endpoint calls or modifications; local prompt and egress markers exercise detection without capturing text.

## Reproduce
From a clean checkout with Python 3.13:
```sh
python -m unittest discover -s tests -p 'test_runtime_soc.py' -v
python -m tower.runtime_soc --output runtime-soc-evidence
(cd runtime-soc-evidence && sha256sum -c SHA256SUMS)
```
GitHub Actions publishes the JSON and SHA256SUMS. The report is the machine-readable export: inspect metrics, correlated cases and response timelines. The digest makes later changes detectable only if independently retained; it does not make the repository immutable. The reported revision is the executed checkout, upstream pins identify the source contract. No output includes raw prompts, model payloads, credentials, approvals, actual identities or PHI.

## Analyst / incident-owner runbook
1. Confirm source version, expected fixture count and telemetry coverage. A missing receipt is a gap, not a clean result.
2. Review correlated cases and rule IDs AI-01 (prompt marker), AI-02 (tool denial), AI-03 (synthetic egress marker), AI-04 (workflow denial); validate context and distinguish benign hits.
3. Analyst proposes a synthetic review ticket; incident-owner role evaluates rationale, separately approves the exact action or leaves it pending. Automated fixture role is not independently authenticated human approval. No ticket is created on denied cases. Replay after execution is rejected. The exercise records one in-memory mock effect only; never perform endpoint containment.
4. Verify effect and record closed/pending state; export and verify the report digest. Escalate missing telemetry, false positives and false negatives to lab owner for corrective tuning and retest.
5. Prior to any stronger claim, require actual independent review, execution-integrity PR integration, external SIEM/EDR handoff if in scope, and durable audit custody.

## Prespecified population and metrics
15 authored cases, 8 positive and 7 negative, including a marker collision, unsupported wording, and a deliberately missing event. Denominator is all cases including missing evidence; distinguish 14/15 delivery coverage from rule coverage. Precision and recall describe this small deterministic population, not a real attack-success or generalized security rate. Timestamps and response stage times are simulated; local processing duration is measured. An operator must review the evidence and independently approve any formal closure. See CI for observed results rather than treating expected values as measurements.
