# AI security program delivery: bounded adoption rather than automatic release

**Independent synthetic portfolio case study.** This is not a CISA delivery, client engagement, production AI system or claimed FedRAMP authorization. Source baseline: `11fc00f45ac5f0cea85dbd668a9b6305fbef3c6f` on `feat/security-program-control-tower`. Written November 7, 2026.

## Problem, stakeholders and scope

A program owner needs to turn security findings and vendor assurance gaps into owned, prioritized work while preventing an AI draft from becoming an unreviewed action. The modeled users are a security analyst, program owner, risk approver and executive reader. These are design personas, not interviewed customers. Success is a traceable decision and evidence package, including a defensible decision **not** to release AI drafting when quality is insufficient.

The existing Control Tower accepts six synthetic fixtures, assigns authored NIST mappings, tracks dependencies and milestones, requires exact-payload review, and exports a dashboard and evidence archive. This extension adds an explicit delivery narrative, selected-control readiness evidence and a local privileged-access simulation. It does not replace the existing implementation, deploy services or alter its live AWS storage.

## Delivery plan and acceptance gates

| Increment | Delivered artifact | Acceptance gate / evidence |
|---|---|---|
| Intake and prioritization | `tower/fixtures.json`, `tower/core.py` | Reject conflicting records, missing dependencies and cycles; transparent likelihood × impact score |
| Decision boundary | `app/workflow.py`, `tower/core.py` | Unapproved, expired and altered requests fail; review binds the exact payload |
| Delivery tracking | `tower/store.py`, `tower/report.py` | Closure needs evidence and completed dependencies; repeated local execution does not create a second ticket |
| AI evaluation | Project 4 comparison and review | Require human-quality gate as well as structural checks; retain blocked decision |
| Governance extension | This case study and selected-control package | Every mapping includes evidence and a gap; no compliance or production claims |
| Access extension | Local privileged-access demo and tests | Action/resource scope, distinct simulated personas, expiry, denial, replay and audit tests |

## Technical feasibility and alternatives

Use local SQLite for a repeatable low-cost program demonstration and keep optional AWS storage behind a separate adapter. Conditional state changes were chosen over direct remediation because a synthetic ticket is sufficient to demonstrate approval and dependency control without touching a real system. A reference draft remains available without a model call. AI prose is untrusted, and application-owned authoritative fields cannot be supplied by the model. The new access demo is a simulation, not a newly deployed IAM role: enforcing actual identity separation would require identity-provider integration, administrator isolation and separately approved deployment.

## Risks and roadblocks

- **Unsafe autonomy:** separate proposal, approval and execution; no remediation tools exposed to the model.
- **Quality overclaim:** structural checks alone do not establish usefulness. Keep release blocked after the observed human-review shortfall.
- **Concurrency/replay:** existing local tests exercise 16 parallel requests with one ticket; cloud concurrency remains unvalidated.
- **Evidence credibility:** synthetic fixtures, a single self-reviewer and editable local audit records cannot support independent assurance.
- **Budget/access:** this extension uses offline Python only. No new AWS cost is incurred by these commands. Existing AWS billing is not measured here.
- **Schedule/publication:** prepare and verify locally; repository publication and live identity enforcement remain separate decisions.

## KPIs and decision

Historical measurements are from committed project records, not newly repeated live AI experiments:

| Metric | Recorded result | Interpretation |
|---|---|---|
| AI structural contract checks | 36/36 per configuration | Necessary but insufficient |
| Human draft quality | 9/12 per configuration vs 12/12 criterion | Both configurations ineligible; gate remains **BLOCKED** |
| Calls | 24 total across two configurations | Small development set, not representative field performance |
| Fixture routing | TP3 / FP1 / TN1 / FN1, accuracy 4/6 | Authored synthetic routing, not AI detection accuracy |
| Local repeat safety | 16 requests, 1 ticket, 15 repeats | Existing local concurrency test, not AWS validation |
| Review/effort savings | Unmeasured | Do not claim ROI or hours saved |

The quality criterion was set retrospectively and the dataset was used during development. The next decision needs a prespecified rubric, held-out data, independent reviewer and scoped live-runtime validation. The launch outcome is a usable **lab demonstration**, not production AI adoption.

## Interview summary

“I built an independent AI security-program lab that connects intake, risk, human decisions, dependency tracking and evidence. I used explicit acceptance gates and negative tests rather than relying on a successful demo. The important decision was to keep AI drafting blocked when human quality review failed, even though structural checks passed. I then extended the governance evidence and a synthetic privileged-access workflow while keeping the limitations visible.”

## Sources

- [Control Tower architecture](../control-tower.md)
- [Historical validation](../control-tower-validation.md)
- [AI final decision](../p4-final-results.md)
- [Governance matrix](../p4-governance-matrix.md)
- [AWS deployment record](../control-tower-aws.md) (historical; not revalidated here)
