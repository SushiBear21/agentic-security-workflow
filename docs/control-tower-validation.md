# Control tower validation — November 3, 2026

Observed locally on Windows / Python 3.13:

- Full repository unittest discovery: **36/36 passed** (16 original security tests,
  20 control-tower tests).
- Compile check for `app`, `tower`, `tests`: passed.
- `git diff --check`: passed.
- Local CLI: ingested six synthetic findings, created three reference proposals,
  exported dashboard and evidence ZIP; package verification returned `True`.
- No real proposal was approved or executed. Approval/execution behavior was
  exercised only inside isolated unit-test temporary databases.
- Concurrent local test: 16 execution requests, one created ticket, 15 idempotent
  repeats, one persisted ticket.
- Fixture routing: TP 3, FP 1, TN 1, FN 1. Review/effort savings remain unmeasured
  in the delivered demo. These are development fixtures, not model accuracy.

Verification limits and publication status:

- AWS STS returned `NoCredentials`; no AWS profile was listed. CloudFormation
  service validation, account inventory, live DynamoDB/S3 tests, live Bedrock calls,
  IAM verification and billing observations were not performed. The JSON template
  was parsed and its storage-only/private settings checked in local tests.
- No new cloud resources, credentials, permissions or paid model calls were made.
- Git push initially failed because the sandbox could not use Windows Credential
  Manager. The escalated push was rejected by automatic approval review because
  exact publication to `SushiBear21/agentic-security-workflow` was not considered
  explicitly authorized. Nothing was pushed. A remote heads read returned no
  `feat/security-program-control-tower` branch.
- Browser visual QA was blocked: the browser URL policy disallowed the local
  `file:` preview protocol. No alternate preview surface was used after that denial.
  HTML generation, escaping and evidence integrity are covered by tests, but visual
  layout has not been browser-verified.

Required decisions before continuation: explicitly authorize publication of the
named feature branch to the named repository; supply an existing authorized
temporary AWS session and approve account, region, resource footprint, spending
ceiling and retention before any deployment. Approval for this synthetic program
does not authorize live response actions in the old lab.
