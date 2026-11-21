# Tracker audit reviewer packet

This is a preparer packet for the synthetic tracker lab. Its supporting CI
artifacts are actual GitHub Actions records from a service using fictional data.
The workpapers address selected controls. Independent review and owner approval
are pending.

- [SOC 2 readiness scope, observation period, and workpapers](soc2-tracker-readiness.md)
- [ISO/IEC 27001:2022 scope, risks, sample Statement of Applicability and workpapers](iso27001-tracker-internal-audit.md)

## Evidence requests

The evidence period is [the tracker observation window](soc2-tracker-readiness.md#system-and-evidence-period) for every row. **November 27, 2026** is an exercise due date for each request. Owner labels refer to proposed lab roles.

| Request | Control workpaper | Owner | Source and status | Finding |
| --- | --- | --- | --- | --- |
| ER-01 · Workspace access and review tests | S2-01, ISO-02 | Access owner | CI-01–03 report the checks by name. `tests/test_tracker.py` reperforms role isolation and credential separation. Fulfilled for authentication, role isolation, digest binding, and audit export on the tested paths. | — |
| ER-02 · Access lifecycle | S2-01, ISO-02 | Access owner | Grant, revocation, and periodic review records missing. | E-01 |
| ER-03 · Change review and promotion | S2-02, ISO-02 | Release coordinator | CI-01–03 and PRs #13 and #14. Technical evidence and traceability present. Insufficient for independent approval and promotion. | E-02 |
| ER-04 · Failed candidate and recovery | S2-03, ISO-04 | Service operator | CI-01–03. Fulfilled for CI failure detection and recovery. | — |
| ER-05 · Ongoing monitoring response | S2-03, ISO-04 | Service operator | Alert delivery, acknowledgement and resolution records missing. | E-03 |
| ER-06 · Retention and reproducibility | ISO-03 | Release coordinator | CI-01–03, a modified copy of CI-01, and the [GitHub API snapshot](audit-evidence/github-api-snapshot.json). Fulfilled for the integrity and decision retests. Retention operation pending. | ISO-F01 |

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

## Retention procedure (ISO-F01)

1. Before any sampled artifact expires, the release coordinator captures GitHub
   artifact and run metadata into `audit-evidence/github-api-snapshot.json`.
2. Monthly, and after any change to the evidence files, the coordinator runs
   `python -m tracker.audit_workpapers` and keeps the CI `tracker-audit-packet` artifact.
3. The coordinator records each check in the PR or an issue with the date and result.

Residual risk: the snapshot sits in the same repository as the archives. The
independent reviewer's PR #14 comment records the GitHub digests outside the
repository contents. Inner-file tampering is covered by synthetic unit-test fixtures,
and the packet's own negative retest covers an altered outer archive.

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
