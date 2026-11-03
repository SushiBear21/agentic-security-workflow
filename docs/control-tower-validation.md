# Control tower validation — November 3, 2026

## Subsequent verified progress

The feature branch was published after repository-specific approval. GitHub
security-test and Project 4 regression workflows passed for commit
`852ec5407ed6b47e74d99823240367e801b21598`. The dashboard was visually checked via
permitted localhost HTTP preview; that preview server was stopped afterward.

Following SSO refresh and explicit cloud spending approval, the storage stack
reached CREATE_COMPLETE. Live synthetic intake, duplicate handling, unapproved
execution denial and private evidence upload/download verification passed. Six
findings and three pending proposals are stored; no approvals, tickets or model
calls were created. See [deployment details and limits](control-tower-aws.md).

The sections below preserve the original local-validation record and blockers as
they stood before those follow-up steps; publication, preview and AWS access are
no longer blocked. Broader live approval/concurrency/IAM and model validation
remain outstanding.

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
