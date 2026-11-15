# Synthetic System Security Plan — Portfolio AI Security Control Tower

**Laboratory exercise, version 1, November 15, 2026. No authorization or
certification is asserted. This is not an official FedRAMP template submission.**

## System description and purpose

The fictional system supports security-review prioritization, advisory draft
remediation, exact-payload decisions, synthetic tickets and executive metrics.
A separate reference evaluation companion tests bounded context handling.
The model does not receive approval or execution authority.

Data is synthetic finding/vendor evidence and pseudonymous test activity.
No federal information, real customer data or production secrets are intended.
An actual FIPS 199 categorization and selected baseline have **not** been performed;
the ten mapped controls are a deliberately limited learning scope.

## Boundary and components

| Component | Included behavior | Boundary/gap |
| --- | --- | --- |
| Python Control Tower | Validation, advisory drafting, risk/dependency register, tickets | Local operator controls the process |
| Local SQLite store | Transactional state and audit chain | No independent immutable audit |
| Optional AWS DynamoDB/S3 | Versioned state and private evidence export | Existing deployment requires fresh configuration verification |
| Read-only staging HTTP service | Synthetic health/metrics on port 8080 | No authentication; private staging network only |
| GitHub Actions | Tests, container scan/SBOM, evidence artifacts | Repository/environment protection configured externally |
| Optional ECS delivery | Existing service image revision update and rollback | No infrastructure provisioning; live target not configured here |
| Bedrock drafting | Advisory text only | Live quality remains blocked |
| Project 4 reference runner | Synthetic evaluation and resilience checks | Offline reference behavior is not live model performance |

Trust boundaries: untrusted finding text to application validation; model output
to advisory fields; operator decision to exact digest; application to local/AWS
storage; reviewed source and image to deployment identity.

## Identities, access and separation of duties

The requester, approver and executor in the access lab are **simulated personas**.
The same OS user can impersonate them. Allowlisting, expiry, revocation and
single-use behavior are tested, but independent authentication is an open gap.
The optional deployment workflow uses GitHub OIDC and a protected staging
environment. Before use, configure independent reviewers, prevent self-review,
restrict the environment to main and restrict OIDC trust to that environment.
No real AWS role or credential is created by this package.

## Data protection and audit

The local demonstration keeps synthetic data in SQLite and evidence ZIPs.
Hashes detect modifications but do not prevent an administrator from rewriting
a file and its manifest. Existing AWS templates request private storage; actual
settings must be collected and reviewed. No encryption, retention or logging
compliance is inferred from a template alone. Keep live evidence private and
exclude identifiers/secrets from public commits.

## Selected control implementations

The authoritative per-control statements, evidence paths and gaps are
[readiness-controls.json](readiness-controls.json). Each selected control has an
open, owned entry in [poam.json](poam.json).

| Controls | Implementation summary | Remaining responsibility |
| --- | --- | --- |
| AC-3, AC-5, AC-6 | Scoped simulated grants, distinct personas, expiry/revoke | Authenticate independent identities and verify deployed IAM |
| AU-2, AU-3, AU-9 | Timestamped actors/actions, hashes, integrity verification | Protect audit storage and anchor evidence independently |
| CA-7 | Repeatable CI plus freshness evaluation | Collect representative operational evidence and review drift |
| CM-3 | Versioned changes, reviewed deployment digest, rollback tests | Configure independent production change authority |
| RA-5 | Dependency and OS/library scans, synthetic finding intake | Confirm actual asset scope, scan coverage and triage |
| SI-2 | Dependency-aware synthetic ticket closure | Apply/verify real fixes with retained evidence |

## Monitoring, incident handling and contingency

[monitoring-plan.json](monitoring-plan.json) defines evidence owners, freshness
periods and response actions. The monitor marks missing, stale, tampered, future
or failed evidence explicitly. Scheduled GitHub scanning refreshes only CI/image
evidence; it is not an AWS continuous-monitoring service.

On suspicious output or failed controls: stop AI-assisted actions, preserve
evidence, open a tracked finding, investigate and rerun the relevant tests.
Do not loosen quality targets to produce a passing result.
Local restore and container tests are automated. ECS rollback is implemented
but requires a configured staging service and a real execution record.

## Authorization status and review

Status: **not authorized for production**. The AI-quality gate remains blocked.
All POA&M entries are open planning items with synthetic owners and proposed
milestones, not commitments by real organizational officials.
Review this SSP whenever the boundary, identity, model, data or deployment changes.

Reference concepts: [NIST SP 800-53](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final),
[FedRAMP SSP training](https://www.fedramp.gov/resources/training/200-A-FedRAMP-Training-FedRAMP-System-Security-Plan-SSP-Required-Documents.pdf),
[FedRAMP POA&M guide](https://www.fedramp.gov/resources/documents/CSP_POAM_Template_Completion_Guide.pdf).
These references do not convert this exercise into a submission-ready package.
