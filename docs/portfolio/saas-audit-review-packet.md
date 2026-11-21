# Two-product SaaS audit evidence packet

This readiness exercise uses fictional commercial AWS services, fixtures, dates
and job roles. The tracker CI rehearsals linked below are verified GitHub Actions
records for a different lab boundary. No AWS resources were provisioned for this
exercise. The selected mappings support evidence planning for a future engagement.

## Service boundaries and ownership

| Boundary | Components, data and flows | Owner and exclusions |
| --- | --- | --- |
| Product A · Evidence Intake | Separate workload account and VPC. An illustrative authenticated API accepts synthetic evidence metadata and ZIPs, persists metadata and stores archives in an A-owned S3 bucket. Tenant role decisions and application audit events originate here. | Product A Access Owner owns identity grants and revocations. Product A Service Owner owns API, database and bucket controls. Customer identity administration and Product B stores are outside A. |
| Product B · Remediation Board | Separate workload account and VPC. An illustrative worker and dashboard use a B-owned DynamoDB inventory and ECR image. The worker ingests approved, redacted status summaries through an export interface and never receives the original ZIPs. | Product B Release Owner owns product changes. Platform Operations owns B inventory remediation. Product A runtime, customer systems and external deployment are outside B. |
| Shared AWS foundation | The management account owns the organization trail and workload-OU guardrail. The security account owns the Config aggregator. The log archive account owns the central bucket. Both workloads feed AWS management events toward the archive in the design. | Cloud Security owns shared account and policy design. Evidence Operations owns log delivery and archive records. Monitoring Lead owns the shared monitoring evidence. CJI, production data and external authorization are outside both lab scopes. |

Each product can reference the same foundation policy, central logging setup
and monitoring process because these are managed once for the workload OU.
Each still owes enrollment, product event selection and delivery, an in-scope
asset inventory, and handling of gaps. Product access, tenant segregation,
release approvals, image promotion and remediation records belong to each
product separately. An organization trail does not establish application-event
coverage. Customer approval and provider control inheritance need documented
responsibility and scoped evidence before use in a real engagement.

Foundation design and simulated drift come from the [#20 landing-zone walkthrough](https://github.com/SushiBear21/agentic-security-workflow/blob/a7f5c38ad62f14eddb298ca546abd76ddd6a82f8/docs/portfolio/cloud-and-ai-governance-drills.md#multi-account-aws-landing-zone).
The input fixture reuses the three asset observations, unverified S3 logging
status and SYN-003 before/after records from the pinned
[#22 monitoring fixture](https://github.com/SushiBear21/agentic-security-workflow/blob/3a5e276bfe064f14ae0e4b32b2173d1a4f00d850/tests/fixtures/conmon-aws-v1.json).
The DynamoDB sample is assigned to Product B in this exercise. The S3 and ECR
IDs remain monitoring fixture aliases, with no claim of product-wide coverage.
The Product A role changes are new simulated observations.

## Selected evidence crosswalk

Framework references are planning correspondences. The same source can support
multiple questions when the boundary, control objective and population match.

| Control and ownership | FedRAMP Rev. 5 Moderate | SOC 2 Type II | ISO/IEC 27001:2022 | CJIS policy v6.0 | Evidence and limits on reuse |
| --- | --- | --- | --- | --- | --- |
| SH-LOG · shared Cloud Security and Evidence Operations, product event coverage retained by service owners | AU-2, AU-6 | CC7.2 | A.8.15, A.8.16 | AU-2, AU-6 | [#20 design](https://github.com/SushiBear21/agentic-security-workflow/blob/a7f5c38ad62f14eddb298ca546abd76ddd6a82f8/docs/portfolio/cloud-and-ai-governance-drills.md#multi-account-aws-landing-zone) and SAAS-ER-02. Shared configuration design applies to both products. FedRAMP event selection and review parameters, SOC period-wide monitoring, ISO applicability and record handling, and CJIS event coverage and applicable policy parameters remain untested. SAAS-G01. |
| SH-MON · shared Monitoring Lead, inventory and response retained by product owners | CA-7, RA-5 | CC7.1, CC7.2 | A.8.8, A.8.16 | RA-5, SI-4 | SAAS-ER-04 and [#22 monitoring documentation](https://github.com/SushiBear21/agentic-security-workflow/blob/3a5e276bfe064f14ae0e4b32b2173d1a4f00d850/docs/portfolio/aws-conmon-synthetic.md). A fixture freshness check can be reused as a method. FedRAMP reporting and scan cadence, SOC period coverage, ISO process evaluation and CJIS scoped monitoring require additional records. SAAS-G02. |
| A-ACCESS · Product A Access Owner | AC-2 | CC6.2, CC6.3 | A.5.16, A.5.18 | AC-2 | SAAS-ER-01. Mock grant and revocation demonstrate the test. They leave periodic review, full account population, FedRAMP parameters, SOC period operation, ISO SoA applicability and CJIS personnel/account context open. Product B needs its own population. |
| B-PATCH · Product B Platform Operations | SI-2 | CC7.1 | A.8.8 | SI-2 | SAAS-ER-03, source SYN-003. The fixture supports test design. FedRAMP remediation deadlines and reporting, SOC sustained operation, ISO treatment records and CJIS patch requirements need actual samples. A's patch coverage cannot inherit B's retest. |
| B-CHANGE · Product B Release Owner | CM-3 | CC8.1 | A.8.32 | CM-3 | SAAS-ER-05. The [tracker rehearsal](tracker-audit-review-packet.md#sample-trace) supplies a test design only. FedRAMP controlled-change evidence, SOC sampled approvals, ISO process records and CJIS approval evidence require product-specific evidence. SAAS-G03. |
| Tracker records · Release Coordinator | AU-11 (potential analogy) | CC7.2 (supporting records only) | A.5.33 | AU-11 (potential analogy) | [ER-06 / ISO-F01](tracker-audit-review-packet.md#retention-procedure-iso-f01). A verified CI ZIP demonstrates integrity for the tracker scope. It supplies no AWS product log retention evidence, period-wide operation or independent archive custody. |

References: [FedRAMP Rev. 5 baseline materials](https://www.fedramp.gov/rev5/agency-authorization/),
[AICPA Trust Services Criteria](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022),
[ISO/IEC 27001:2022](https://www.iso.org/standard/27001),
[FBI CJIS Security Policy v6.0](https://le.fbi.gov/file-repository/cjis_security_policy_v6-0_20241227.pdf).
The audit date and applicability determine which framework edition and parameters
a real engagement should use.

## Mock period and review samples

The mock period is November 1–20, 2026, inclusive. All requests are due November
20 in the simulation. The [input fixture](audit-evidence/saas-audit-fixture.json)
and generated JSON trace each request to its source and evaluation.

| Request | Control and owner | Source, population and result |
| --- | --- | --- |
| SAAS-ER-01 | A-ACCESS · Product A Access Owner | Both fixture role changes tested. A-01 Nov 10 approved grant allows access. A-02 Nov 12 approved revocation denies access. Fulfilled. |
| SAAS-ER-02 | SH-LOG · Evidence Operations | Sole synthetic S3 logging observation is unverified. Underlying observation timestamp and product delivery receipts are absent. Insufficient. SAAS-G01. |
| SAAS-ER-03 | B-PATCH · Platform Operations | Entire fixture population of one tracked DynamoDB remediation. Oct 3 baseline brought forward, Nov 6 in-period retest. Fulfilled request, failed baseline, passing retest. SAAS-F01. |
| SAAS-ER-04 | SH-MON · Monitoring Lead | All three fixture assets evaluated as of Nov 20. S3 Nov 18 current, DynamoDB Oct 15 stale under the fixture's 30-day rule, ECR missing. Insufficient. SAAS-G02. |
| SAAS-ER-05 | B-CHANGE · Product B Release Owner | No change population or approval/promotion receipt provided. Zero samples tested. Missing. SAAS-G03. |

For SAAS-F01, SYN-003-BEFORE at 14:00 UTC on October 3 failed because
remediation confirmation was absent. This could allow a flaw to be reported as
fixed without supporting evidence. Platform Operations recorded the simulated
confirmation and repeated the same test on the same asset and control.
SYN-003-RETEST at 14:00 UTC on November 6 passed. The upstream fixture marks
SYN-003 closed. The preparer records a passing simulated retest and leaves
independent reviewer disposition and owner closure pending for SAAS-F01.

The JSON packet records impact, cause, owner, action and retest status for each
gap. The existing [tracker register and workpapers](tracker-audit-review-packet.md)
separately trace the three verified CI rehearsals, E-01 through E-03, and
ISO-F01. These AWS fixtures do not resolve the tracker access lifecycle,
approved promotion or alert-response findings.

## Independent review

Run `python -m tracker.saas_audit --output saas-audit-packet.json` and
`python -m tracker.audit_workpapers --output tracker-audit-packet.json` from the
repository root. Compare the generated output with this packet and the pinned
upstream fixture. Reperform one passing sample and SAAS-F01. Check the missing
population and the distinction between shared design and product operation.
For ISO-F01, independently obtain the source metadata while available and
retain the record under reviewer control. Compare the ZIPs and the exact CI
revision, and record what can be concluded after expiry.

| Record | Status |
| --- | --- |
| Independent reviewer identity, independence attestation, date and reviewed commit | Pending |
| Sample IDs, reperformance results and per-finding disposition | Pending |
| Independent evidence custody reference and retention-cycle assessment | Pending |
| Lab owner approval, residual-risk acceptance and closure after review | Pending |
