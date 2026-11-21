# Tracker audit reviewer packet

This is a preparer packet for the synthetic tracker lab. Its supporting CI
artifacts are actual GitHub Actions records from a service using fictional data.
The workpapers address selected controls. Independent review and owner approval
are pending.

- [SOC 2 readiness scope, observation period, and workpapers](soc2-tracker-readiness.md)
- [ISO/IEC 27001:2022 scope, risks, sample Statement of Applicability and workpapers](iso27001-tracker-internal-audit.md)

The [two-product SaaS evidence packet](saas-audit-review-packet.md) exercises the separate simulated AWS boundary and period.

## Evidence requests

The evidence period is [the tracker observation window](soc2-tracker-readiness.md#system-and-evidence-period) for every row. **November 27, 2026** is an exercise due date for each request. Owner labels refer to proposed lab roles.

| Request | Control workpaper | Owner | Source and status | Finding |
| --- | --- | --- | --- | --- |
| ER-01 · Workspace access and review tests | S2-01, ISO-02 | Access owner | CI-01–03 report the checks by name. `tests/test_tracker.py` reperforms role isolation and credential separation. Fulfilled for authentication, role isolation, digest binding, and audit export on the tested paths. | — |
| ER-02 · Access lifecycle | S2-01, ISO-02 | Access owner | Grant, revocation, and periodic review records missing. | E-01 |
| ER-03 · Change review and promotion | S2-02, ISO-02 | Release coordinator | CI-01–03 and PRs #13 and #14. Technical evidence and traceability present. Insufficient for independent approval and promotion. | E-02 |
| ER-04 · Failed candidate and recovery | S2-03, ISO-04 | Service operator | CI-01–03. Fulfilled for CI failure detection and recovery. | — |
| ER-05 · Ongoing monitoring response | S2-03, ISO-04 | Service operator | Alert delivery, acknowledgement and resolution records missing. | E-03 |
| ER-06 · Retention and reproducibility | ISO-03 | Release coordinator | CI-01–03, a modified copy of CI-01, and the [GitHub API snapshot](audit-evidence/github-api-snapshot.json). Fulfilled for the integrity and decision retests. First source metadata check recorded. Recurring retention evidence pending. | ISO-F01 |

## Sample trace

| Sample and timestamp (UTC, run creation) | Linked evidence | Workpaper result |
| --- | --- | --- |
| CI-01 · Nov 18, 06:12:46 | [Tracker PR #13 rehearsal](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44249673451) · [Retained ZIP](audit-evidence/tracker-ci-original.zip) | ER-01 and ER-04 verified. ER-03 technical gates reperform with promotion unauthorized. ER-06 original accepted and altered copy rejected. |
| CI-02 · Nov 18, 16:08:59 | [Audit PR #14 rehearsal](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44343819472) · [Retained ZIP](audit-evidence/tracker-ci-44343819472.zip) | ER-01 and ER-04 verified. ER-03 technical gates reperform with promotion unauthorized. ER-06 original accepted. |
| CI-03 · Nov 18, 16:09:29 | [Audit PR #14 release rehearsal on fix commit c4aee81](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44343909793) · [Retained ZIP](audit-evidence/tracker-ci-44343909793.zip) | ER-01 and ER-04 verified. ER-03 technical gates reperform with promotion unauthorized. ER-06 original accepted. |

CI-03 is a release rehearsal on the fix commit. That commit moved the archive
reperformance out of the release workflow, so CI-03 is not the retest record. The
ISO-F01 retest ran in [Agent security tests run 44343910025](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44343910025)
on the same commit. [Run 44773783571](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44773783571)
regenerated the full packet on November 20.

The [GitHub API snapshot](audit-evidence/github-api-snapshot.json) captures the
GitHub-reported artifact digests, expiry dates and run conclusions on November 21,
2026, before the December 18 artifact expiry. The packet build fails if the
population disagrees with it.

The [population snapshot](audit-evidence/tracker-audit-population.json) preserves
run and artifact IDs, checkout and head revisions, UTC dates, and GitHub artifact
digests. The report hashes the retained ZIPs, verifies inner evidence digests,
and re-runs the historical technical release decisions. The
[release workflow at the baseline revision](https://github.com/SushiBear21/agentic-security-workflow/blob/9eeacafdf39bad4c72b4a486062a146f95d74126/.github/workflows/evidence-tracker.yml)
explains how the original test checked the baseline record during CI recovery.

## Findings and disposition

| Finding | Impact and cause | Assigned function and corrective action | Test and disposition |
| --- | --- | --- | --- |
| E-01 · Access lifecycle | Revocation omissions could leave access active. The preparer identified demo credentials and no observed lifecycle records. | Access owner. Document and evidence issuance, revocation and periodic review. | Test approved access, a denied revoked identity and a dated review. Pending. |
| E-02 · Change authorization | Technical eligibility alone cannot establish authorization to promote. The workflow stops at technical review. | Release coordinator. Retain formal approval and a lab promotion receipt tied to the reviewed revision. | Reconcile approval, revision and promotion when evidence exists. Pending. |
| E-03 · Monitoring response | A service failure outside CI may go unnoticed. The observed workflow covers startup and smoke checks. | Service operator. Capture a lab alert route, acknowledgement and resolution. | Trace timestamped alert through response and verify closure. Pending. |
| ISO-F01 · Evidence records | An altered or unreproducible archive could be relied on. The original release procedure omitted post-download verification. | Release coordinator, held by the lab owner. Preserve and digest-check the originals, snapshot GitHub metadata before each artifact expiry, and rerun the packet monthly. | Three original ZIPs reproduced their decisions and the modified copy was rejected (run 44343910025). Digests reconcile to the GitHub API snapshot. Technical retest passed. Periodic retention evidence and independent closure pending. |

## Supplemental tracker operating retest

The historical request register and three CI samples above retain their original
observation period. A later CI run collects one new sample for each open tracker
finding. It runs the actual tracker HTTP handler on ephemeral loopback ports with
a temporary SQLite database and random lab credentials.

| Historical request and finding | Supplemental lab sample and pass criteria | Scope remaining for review |
| --- | --- | --- |
| ER-02 / E-01 | LC-01. The fictitious contributor receives a recorded grant. HTTP session checks return 401 before issuance, 200 with the expected role after issuance, and 401 after removal and service restart. The existing reviewer returns 200 and a dated inventory review reconciles both active roles. | One lifecycle and one review of file-backed demo credentials. |
| ER-03 / E-02 | PRM-01. Stage the checkout with the same lab database and active credential set. Block missing approval, wrong-revision approval and same-actor approval. A matching fixture approval binds the checkout, runtime source hashes, staged smoke receipt and local target. Start the approved local slot and verify its smoke check, audit export and preserved staged record. | One localhost promotion with a simulated approver. Existing container rehearsals remain technical gates with promotion unauthorized. |
| ER-05 / E-03 | INC-01. Stop the promoted listener. An external-to-server HTTP health probe detects the refused or timed-out connection, routes a local notification and records simulated acknowledgement. Restart on the same endpoint, verify HTTP 200 and preserve the promoted evidence record before recording resolution. | One injected outage. Alert routing uses an in-process test queue and acknowledgement is simulated. |

Run from the exact clean checkout with Python 3.13:

```sh
python -m tracker.operating_evidence --revision "$(git rev-parse HEAD)" --output tracker-operating-evidence.json
```

The security workflow records its actual checkout SHA and publishes the
`tracker-operating-evidence` JSON artifact, including UTC times, access results,
promotion receipt and incident journal. The independent reviewer should reconcile
that artifact with the run and reperform the checks before recording a disposition.
See [PR #24](https://github.com/SushiBear21/agentic-security-workflow/pull/24)
for the exact run and artifact. All closure decisions remain pending.

## Retention procedure (ISO-F01)

1. Before expiry, preserve the artifact and run metadata and verify the retained
   ZIPs. On November 21, the preparer queried GitHub and reconciled all three
   source artifacts to the recorded IDs, digests, head SHAs and expiry dates.
   See the [first source check](audit-evidence/iso-f01-first-source-check.json).
2. [Tracker audit retention](../../.github/workflows/tracker-audit-retention.yml)
   runs on evidence changes in the PR and at 15:23 UTC on the first day of each
   month once present on the default branch. It reruns the full packet, checks
   live metadata while each source remains within its retention window, and
   labels checks after source expiry as using the captured snapshot. It uploads
   a dated report with the checkout revision, source status and archive results.
3. The release coordinator records the run link and findings at each cadence,
   investigates a missed or failed run, and arranges reviewer-controlled custody
   of the source digest and run metadata before the earliest expiry on December
   18, 2026 at 06:14:07 UTC. CI reports have a 90-day retention setting and
   require separate preservation for longer review periods.

The lab owner controls the snapshot, the retained archives and the editable
[simulated Greg GRC comment](https://github.com/SushiBear21/agentic-security-workflow/pull/14#issuecomment-7056332096).
A separate human reviewer must capture or hold the source record under their
own custody. ZIP verification tests address accidental or detectable changes.
A coordinated rewrite of same-repository inputs remains a residual risk.
The outer archive retest uses an altered historical copy. Inner-file tampering
is covered by synthetic unit-test fixtures. ISO-F01 remains open for periodic
operating evidence, independent custody and closure.

## Reviewer disposition

Use this blank record for a separate review. The owner records risk acceptance
and closure decisions after receiving the review.

| Field | Record |
| --- | --- |
| Reviewer name, role and independence confirmation | Pending |
| Review date and packet revision | Pending |
| Evidence sampled and procedures reperformed | Pending |
| Per-finding decision, rationale, and supporting evidence | Pending |
| Lab owner disposition and risk acceptance reference | Pending |
| Follow-up date and closure decision | Pending |

Produce the full JSON packet locally with
`python -m tracker.audit_workpapers --output tracker-audit-packet.json`.
The regular security workflow generates the same output as the
`tracker-audit-packet` artifact. Current outputs represent the bounded CI
population and selected controls. They provide no independent attestation,
certification, or period-wide operating effectiveness conclusion.
