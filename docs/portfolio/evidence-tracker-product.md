# Evidence tracker product ownership

## One page product brief

**Problem hypothesis.** Security evidence arrives through separate channels and
reviewers may have difficulty determining which version was approved and who
approved it. Validate this through discovery before treating it as a user finding.

**Target users.** A control owner submits an evidence record. A security reviewer
checks the record, records a decision, and exports the audit history for handoff.

**MVP.** Submit a synthetic evidence note, review the exact submitted version,
and export the workspace history. The demo uses a browser, local SQLite, and
preprovisioned contributor and reviewer tokens. Each credential maps to one
workspace. Contributors see their own records and reviewers see their workspace.
There is no user attachment storage, tenant self-service, SSO, or hosted service
in this iteration.

**Proposed outcome measures.** Two testers complete each assigned task without
coaching. Record completion, elapsed time, help requests, and a confidence
rating from 1–5 for each task. Capture a baseline from their current workflow if
they can show it with synthetic data. Treat two sessions as qualitative
discovery and record the limits of the sample. Robert owns the final thresholds.

## Prioritized backlog and acceptance

| Rank | Issue | Acceptance |
| --- | --- | --- |
| P0 | [Submit evidence](https://github.com/SushiBear21/agentic-security-workflow/issues/8) | Contributor submits a valid note, sees a pending item, and cannot list another contributor's records. A retry preserves the original record. |
| P0 | [Review and export](https://github.com/SushiBear21/agentic-security-workflow/issues/11) | Reviewer approves or rejects the exact digest once, with a reason. Export contains the decision and a verifiable event chain. Wrong-role and cross-workspace actions are denied. |
| P0 | [CI/CD release rehearsal](https://github.com/SushiBear21/agentic-security-workflow/issues/9) | CI links issue scope, builds a non-root container, retains scan and SBOM, and demonstrates baseline, blocked candidate, and recovery preserving the approved record. |
| P1 | [Validate discovery and prioritize iteration 2](https://github.com/SushiBear21/agentic-security-workflow/issues/12) | Interview both personas, validate or revise the brief, record usability findings, rank one change and retest it. |
| P2 | [Defer notifications and bulk import](https://github.com/SushiBear21/agentic-security-workflow/issues/10) | Robert confirms the tradeoff or proposes an alternative. Revisit when discovery shows a recurring need. |

## Two user discovery guide

Schedule one short session per persona. Ask them to use sanitized examples.
Record notes under `Observation`, `Interpretation`, and `Open question`.

| Participant | Questions |
| --- | --- |
| Contributor | Walk through a recent evidence submission. Where did you spend the most time? How did you know a reviewer received the right version? How would you know what happened after submission? |
| Reviewer | Show how you decide which evidence to accept. What makes you reject it? How do you reconstruct who approved a version? Who consumes the export and what do they need from it? |

Acceptance is one cited observation from each persona, one validated or rejected
hypothesis, and Robert's confirmation of the most important user problem.
**Status:** interviews and findings pending.

## MVP decision log

| Decision | Options and tradeoff | Owner and state |
| --- | --- | --- |
| MVP order | Prioritize submit, review and export over dashboards because they cover the full evidence handoff. This is a hypothesis. | Robert, proposed pending discovery |
| Deferral | Defer notifications and bulk import to keep the lab focused on review integrity and role separation. Revisit if users repeatedly miss reviews or have high-volume evidence intake. | Robert, proposed pending confirmation |
| Iteration 2 | Select one usability improvement after testing and record the observation that changed the priority. | Robert, pending tester evidence and decision |

## Usability session script

Run the [local demo](evidence-tracker-release.md). Give the contributor and reviewer
separate tokens. Ask them to think aloud and avoid coaching until stuck.

1. **Submit.** Give the contributor a title and fictional checklist note. Ask
   them to submit it and tell you how they know it entered review. Success is one
   pending record with the expected title and note.
2. **Review.** Give the reviewer the title. Ask them to locate it, explain their
   decision, and record that decision. Success is the expected status, reviewer
   name and rationale on the matching evidence record.
3. **Export.** Ask the reviewer to export an audit history and find the item and
   its submit and review events. Success is a readable JSON export with all
   expected records and events.

Capture task, test date, participant alias, completion, elapsed time, hints,
confidence, and observed friction. Acceptance is one record per assigned task
and enough detail to reproduce any blocker. No findings have been recorded.

## Second iteration

| Before | Proposed after | Evidence needed |
| --- | --- | --- |
| P1 discovery and usability testing | Incorporate the findings into Robert's MVP decision log | Two sessions and confirmed priorities |
| P2 context for decisions in the UI | Example only. Promote to P1 if testers cannot tell which version they are approving | Quote or observed failure, owner decision, testable change |
| P2 notifications and bulk import | Keep deferred or rerank if supported by the sessions | Explicit tradeoff and follow-up trigger |

Retest the affected task with the same instructions and compare completion,
hints and time with the first run. Record the change even if the result is
inconclusive. Draft release note fields are `version`, `issue`, `user feedback`,
`change shipped`, `retest result`, and `remaining limitation`. Iteration 2
release notes are pending confirmation and implementation of the selected change.
