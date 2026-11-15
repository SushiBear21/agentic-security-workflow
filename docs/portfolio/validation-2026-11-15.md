# Portfolio validation — November 15, 2026

Scope: both the technical-evaluation and program/deployment extension lists.
Existing functionality was inspected in all four repositories. The agent work
extends `feat/security-program-control-tower`; the other changed repositories
start from their current main branches. Threat-intelligence code was reused as
existing portfolio context and its 58-test suite passed unchanged.

## Observed local results

Windows / Python 3.13, with the existing pinned AWS SDK dependency installation:

| Check | Result |
| --- | --- |
| RAG unit tests | 24 passed |
| RAG mocked AWS contracts | 6/6 passed, zero model calls |
| Detection/response unit tests | 29 passed |
| Detection development fixtures | 9/9 correct; TP 4, FP 0, TN 5, FN 0 |
| Agent / Control Tower unit tests | 73 passed |
| Existing Project 4 inline self-tests | 42 passed across six modules |
| Versioned Project 4 context regression | 10/10 passed |
| Existing fallback drill | Broken candidate rejected; reference passed |
| Customer release rehearsal | Unapproved denial, one ticket, verified evidence, exact-state restore passed |
| Lambda packaging | Detector, finding router and response ZIPs built and inspected |
| Existing Terraform formatting | Passed |

The readiness path validator's Windows absolute-path bug was fixed after the
initial test run caught it. The new backup helper explicitly closes SQLite
connections after a Windows file-lock failure in its first test run.

All analyst reviews in the detection dataset remain pending. No human effort
savings, live model accuracy, production availability or compliance outcome is
claimed. A synthetic 5-second review value in the release drill is fixture input.

The release command does not run the unit suite or dependency scanner, so its
own assessment correctly leaves those gates unmeasured. Existing human quality
remains failed. A successful rehearsal exits zero while its readiness decision
remains blocked. No decision here authorizes deployment.

## Hosted and live checks

A dedicated workflow runs the unit suite, versioned regression, release rehearsal,
container build/run and pip-audit. Docker is unavailable locally, and outbound
package/network access is blocked. Container and vulnerability-scan results
must be checked in the hosted workflow; they are not counted as local passes.

No live AWS infrastructure, real privileged session, paid model invocation,
production deployment or independent human evaluation was performed.
Existing Terraform infrastructure was not changed. Governance controls remain
selected synthetic demonstrations, with documented identity and audit gaps.

## Extension mapping

| Extension | Implementation |
| --- | --- |
| RAG security evaluation | Versioned scoring, mocked service runner, settings validation |
| Detection metrics | Existing classifier plus confusion matrix and analyst observations |
| AI governance | Model-risk fields, hash-bound gates, expiring noncritical exceptions |
| Evaluation/reliability | Versioned context suite, traces, p95, lost-acknowledgement test |
| Program Control Tower | Existing intake/approvals/dependencies/dashboard reused in acceptance |
| Privileged access | Existing scoped/expiring grants plus revocation and concurrent single use |
| Federal readiness | Expanded selected-control evidence pack, SBOM and dependency-scan CI |
| Customer deployment | Non-root container, acceptance rehearsal and exact-state rollback |
