# ISO/IEC 27001:2022 internal-audit exercise for the evidence tracker

## ISMS scope and responsibilities

The exercise covers how the synthetic evidence tracker is designed, accessed,
changed in GitHub, tested in CI, and audited. It includes the local browser and
service, workspace SQLite data, lab token provisioning, PR and CI controls,
and the archive of CI evidence. Production hosting, real customer data, AWS
deployment, and external service operations are outside the [lab boundary](cmmc-tracker-assessment.md#ssp-extract-and-boundary).

Proposed roles are the lab owner for scope and risk acceptance, access owner for
token handling, release coordinator for change evidence, and an independent
reviewer for workpaper review and finding disposition. This exercise records
the preparer's tests. The independent reviewer and management acceptance are pending.

## Risk register

Likelihood and impact are each 1–3. The score is likelihood × impact. A score
of 6 or 9 requires priority treatment before a hosted or customer-facing use.
Residual scores are design estimates for this exercise and await owner approval.

| Risk | Initial score | Planned treatment | Residual and status |
| --- | ---: | --- | --- |
| R-01 · Evidence disclosure across roles or workspaces | 2 × 3 = 6 | Enforce scoped role checks and test denials and workspace separation. Use synthetic data and local-only operation. | 1 × 3 = 3 for the lab. Access lifecycle evidence remains open. |
| R-02 · Unapproved or broken change promoted | 2 × 3 = 6 | Tie the change to PR and exact image evidence. Gate unhealthy candidates. Reserve promotion for explicit human authorization. | 1 × 3 = 3 for the lab. An independently approved promotion remains unobserved. |
| R-03 · Release evidence altered, lost, or not independently reproducible | 2 × 3 = 6 | Retain the original ZIP, capture its source digest, and verify the inner receipts and decisions before relying on them. | 1 × 3 = 3 estimated. Technical retest passed. Independent disposition and repeatable retention ownership are pending. |
| R-04 · Service failure missed outside CI | 2 × 2 = 4 | Run health and workflow checks in CI. Define a future alert owner and acknowledgement exercise before hosted use. | 2 × 2 = 4. Continuous telemetry and alert handling remain open. |

## Sample Statement of Applicability

This is an extract for the four scoped risks. A complete SoA would consider
all necessary controls, including whether other Annex A controls are applicable
and whether controls outside Annex A are needed.

| Annex A control | Applicability and rationale | Status and evidence |
| --- | --- | --- |
| A.5.15 Access control | Included to limit evidence by role and workspace (R-01) | Implemented for lab paths. Role and workspace tests in `tests/test_tracker.py`. |
| A.5.18 Access rights | Included because lab credentials should be assigned and revoked appropriately (R-01) | Partially implemented. Credential roles tested. Access review and revocation evidence pending. |
| A.5.33 Protection of records | Included to preserve reliable evidence for review (R-03) | Technical integrity check and retained historical sample implemented in this PR. Retention ownership and independent review pending. |
| A.8.16 Monitoring activities | Included to identify unhealthy tracker changes (R-04) | Implemented in CI for health and smoke checks. Ongoing alerting remains open. |
| A.8.32 Change management | Included because code and runtime changes can affect evidence availability (R-02) | Technical rehearsal verified. Approval and promotion have not been observed. |
| A.7.4 Physical security monitoring | Excluded from this software lab exercise because the lab does not operate a facility and physical monitoring is outside scope | Reassess if a hosted or facility-managed system enters scope. |

## Audit plan and workpapers

**Objective and criteria.** Test selected access, monitoring, change, and evidence
protection procedures and the exercise's proposed risk treatment. Use ISO/IEC
27001:2022 clauses 4.3, 6.1.2–6.1.3, 9.2 and 10.2 as organizing references.
Map each test to the applicable control or risk. This is a limited exercise,
with the independent reviewer to be assigned by the lab owner.

**Sample and method.** Examine the tracker source and release workflow, inspect
three GitHub rehearsals from the [defined evidence period](soc2-tracker-readiness.md#system-and-evidence-period),
and reperform release evidence verification. Follow the [evidence requests and sample trace](tracker-audit-review-packet.md). Include a negative test using a
deliberately altered copy. Keep management approval and reviewer sign-off open
until they are supplied.

| Workpaper | Procedure | Observed outcome |
| --- | --- | --- |
| ISO-01 · Scope and treatment | Compare boundary and role owners to the tracker and release workflows. Trace each risk to a selected control and treatment. | Scope and control map documented. Risk acceptance pending owner confirmation. |
| ISO-02 · Access and change | Inspect role tests and reconcile the CI receipt to the PR, issues, scan and recovery phases. | Selected technical gates observed. Independent change approval and promotion remain unverified. |
| ISO-03 · Records protection | Examine original controls for offline verification of historical evidence. Test the new procedure with the retained ZIP and with an altered copy. | Baseline gap found. The original ZIP reperformed and the altered copy was rejected. See ISO-F01. |
| ISO-04 · Monitoring | Verify that the rehearsal blocked the unhealthy candidate and observed a healthy recovery. | CI monitoring confirmed for all three runs. Continuous monitoring and alert response remain outside the observed sample. |

## ISO-F01 release evidence verification gap

- **Condition and evidence.** The baseline [tracker release workflow](https://github.com/SushiBear21/agentic-security-workflow/blob/9eeacafdf39bad4c72b4a486062a146f95d74126/.github/workflows/evidence-tracker.yml) records input hashes in its receipt. Its [runbook](https://github.com/SushiBear21/agentic-security-workflow/blob/9eeacafdf39bad4c72b4a486062a146f95d74126/docs/portfolio/evidence-tracker-release.md) explains artifact generation but supplies no procedure or tool to check an archived copy against artifact metadata and reperform the decision. The source artifact also has an expiry date.
- **Root cause.** The initial change process specified how to generate and upload evidence. It omitted a post-download verification and retention step for reviewers. This is the preparer's inference from the baseline source and runbook.
- **Corrective action.** The release coordinator now has a documented procedure, three byte-identical [retained artifacts](tracker-audit-review-packet.md#sample-trace) and a [verifier](../../tracker/audit_bundle.py) that checks the ZIP digest, embedded receipt inputs, source revision, and historical decision.
- **Retest.** All three retained archives matched the corresponding captured GitHub digest and reproduced the baseline, blocked candidate, and recovery decisions for each run. A modified copy of the original archive was rejected before any receipt was relied on. The retest record is [Agent security tests run 44343910025](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44343910025) on fix commit `c4aee81`. The digests reconcile to a [GitHub API snapshot](audit-evidence/github-api-snapshot.json) captured before the December 18, 2026 expiry. See the [retest procedure and review record](tracker-audit-review-packet.md#reviewer-disposition).
- **Retention.** The release coordinator role, held by the lab owner, follows the [retention procedure](tracker-audit-review-packet.md#retention-procedure-iso-f01).
- **Disposition.** Technical retest passed for the three selected rehearsals. Retention responsibility is assigned. Operating evidence of the periodic check and independent closure remain pending.

Reproduce using the [SOC 2 workpaper commands](soc2-tracker-readiness.md#evidence-and-reproduction).
Run `python -m unittest discover -s tests -p test_tracker_audit_bundle.py -v`
to test altered inputs and failed recovery evidence without editing the retained ZIP.

[ISO/IEC 27001:2022 standard overview](https://www.iso.org/standard/27001) ·
[ISO committee note on the Statement of Applicability](https://committee.iso.org/files/live/sites/jtc1sc27/files/resources/ISO-IECJTC1-SC27-WG1_N3298_Auditing%20Practices%20Note%20-%20SoA.pdf)
