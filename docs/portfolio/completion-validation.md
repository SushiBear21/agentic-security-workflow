# Remaining deliverables — validation record

November 15, 2026. Extends the previously merged portfolio implementation.

Implemented: synthetic SSP and ten open selected-control POA&M entries;
monitoring plan and freshness/integrity checks; read-only scoped AWS configuration
collector; explicit-cohort adoption calculations; immutable-image ECS plan/apply
with exact-plan approval and guarded rollback; manual build/scan/publish pipeline;
OS/library Trivy scans and container SBOMs; read-only synthetic staging service.

Local Python 3.13 validation: **90 tests passed**, syntax compilation passed,
synthetic adoption CLI produced expected denominators and metrics, and compliance
CLI validated ten open gaps while returning exit 2 for missing operational
evidence. Existing release tests rebuilt/verified the expanded readiness pack.

Container build, vulnerability scan, service smoke test and existing Project 4
workflows run in GitHub. Consult PR checks for their final status. No Docker
runtime was available locally.

AWS publish/deploy workflows are implemented but not executed: protected
environment settings, scoped OIDC roles, target ECR/ECS configuration and live
execution evidence remain required. No new cloud infrastructure or model calls
were made. Adoption results in the fixture are synthetic. This is not an official
SSP/POA&M submission or production-readiness certification.

Container remediation: replaced the Debian runtime with a digest-pinned official
Python 3.13 Alpine runtime and removed pip after dependency installation. The
HIGH/CRITICAL gate includes unfixed findings; no suppression was added.
