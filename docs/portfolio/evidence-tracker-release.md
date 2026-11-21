# Evidence tracker release rehearsal

## Run the local demo

Run the following from the repository root with Python 3.13. Use a new
credential filename when initializing a fresh exercise.

```sh
mkdir -p .local
python -m tracker.server --db .local/evidence.db --credentials .local/tracker-credentials.json --init-demo-credentials
python -m tracker.server --db .local/evidence.db --credentials .local/tracker-credentials.json
```

Open http://127.0.0.1:8090. Read the generated credential file locally and use
the contributor token to submit a fictional evidence note. Sign out and switch
to the reviewer token to approve or reject it and download `evidence-audit.json`.
To verify the workflow programmatically from another terminal, run:

```sh
python -m tracker.smoke --credentials .local/tracker-credentials.json --output .local/tracker-smoke.json
python -m tracker.assessment --output .local/cmmc-exercise.json
```

The smoke exercise writes synthetic records. Keep credentials and exports out
of source control. The localhost demo uses static lab tokens and a hash-linked
trail in the same SQLite database as records. A database administrator could
replace both state and audit data. Hosting it for multiple teams would require
managed identities and credential rotation, TLS, independent log retention,
availability engineering, and a separate security review.

## Change traceability

The release record references [submit #8](https://github.com/SushiBear21/agentic-security-workflow/issues/8),
[release #9](https://github.com/SushiBear21/agentic-security-workflow/issues/9), and [review and export #11](https://github.com/SushiBear21/agentic-security-workflow/issues/11).
A PR-triggered [Evidence tracker release rehearsal](https://github.com/SushiBear21/agentic-security-workflow/actions/workflows/evidence-tracker.yml)
records the PR number, GitHub checkout revision, image config digest, and hashes
for the Trivy, SBOM, and smoke receipts. GitHub Actions retains the raw output
in the `tracker-release-and-assessment` artifact.

## Go or no go

These are proposed roles for the lab. CI records technical eligibility
and does not record human approval automatically.

| Owner | Gate | Pause condition |
| --- | --- | --- |
| Product owner | Core workflow acceptance and issue scope | A core story fails or acceptance remains unconfirmed |
| Release coordinator | Exact revision builds, recovery test succeeds, release notes and rollback decision recorded | Traceability is missing or baseline record is not preserved |
| Security reviewer | Exact scanned image passes the high and critical vulnerability threshold, SBOM exists, role and review tests pass | Scan is stale, missing, nonmatching, or reports a blocking finding |
| Release approver | Review the three machine decisions and explicitly approve promotion | Any gate is blocked or approval is absent |

The workflow exercises one image and two runtime configurations:

1. **Baseline.** Start the container with the lab credentials, submit and
   review over HTTP, then exercise all three workflows in Chromium and verify the audit export.
2. **Blocked candidate.** Restart with a deliberately missing credential file.
   Require a nonzero process exit, the expected file-not-found signal, and
   a failing HTTP smoke receipt. The candidate is ineligible for promotion.
3. **Recovery.** Restart the same image with the known-good credential path
   and the same SQLite volume. Rerun the workflow and confirm the previously
   approved record survives with its original digest.

The expected receipt states are `eligible_for_review`, `blocked`, and
`eligible_for_review`. The workflow fails if it cannot reproduce that sequence.
The recovery exercise validates a runtime rollback in CI. The receipt records
`promotion_authorized: false`, and the workflow uses no AWS services.
