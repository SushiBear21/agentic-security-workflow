# Evidence-bound AI assurance workflow

`tower.assurance.assess(package, root, now)` evaluates a versioned synthetic
model-risk assessment with intended use, failure impact, accountable owner and
trust boundary. Every gate references inventoried files whose SHA-256 hashes
must match before a decision is made.

Required gates: security tests, regression tests, human quality, rollback and
dependency scan. Only dependency-scan risk can be excepted for a local lab review,
with an owner, rationale and future expiry. Security, quality, regression and
rollback gates cannot be waived. Unknown/duplicate exceptions, expired exceptions,
missing evidence and changed hashes fail closed. No result authorizes production.

The gate validates evidence linkage and declared status; it does not authenticate
a reviewer or infer that an arbitrary file proves its claimed status. Local
operators can rewrite files and manifests together. A production workflow needs
trusted signed attestations and independent decision authority.

| Requirement analogy | Existing/new evidence | Open gap |
| --- | --- | --- |
| NIST AI RMF Govern / Map | Model-risk fields; existing program case study | Independent owner and real use-case review |
| NIST AI RMF Measure | Versioned regression, detection and RAG reports | Held-out data and independent live judgments |
| NIST AI RMF Manage | Blocking gates, scoped expiring risk exception | Production decision process |
| NIST 800-53 AC-3 / AC-5 / AC-6 | Allowlisted access, simulated distinct actors, revoke/expiry | Authenticated roles and real least-privilege IAM |
| NIST 800-53 AU-9 / CA-7 | Hash inventories, regression and package verification | Immutable external audit anchor |
| NIST 800-53 CM-3 / SI-2 | Versioned release, rollback drill, dependency scan job | Real image/OS scan and approved release process |

Mappings are illustrative selected-control exercises, not a full baseline or
authorization package. The existing readiness-control inventory remains the
source for explicit scope and gaps.

Privileged access adds approver-only revocation before execution and tests
16 concurrent execution attempts against one single-use grant. The simulator
still accepts caller-supplied actor names; it does not issue AWS credentials.
