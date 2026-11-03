# AI Security Program Control Tower

This additive portfolio module integrates the existing agentic workflow's canonical
payload hashing with program tracking. It carries forward the AWS response lab's
exact-payload decisions, conditional commits, idempotency and fail-closed behavior.
Execution creates a synthetic remediation ticket only. It never changes an ENI,
security group, vendor account or production resource.

## Quick start (Python 3.13)

From the repository root, no dependencies or AWS account are needed for local mode:

```powershell
python -m tower ingest tower/fixtures.json
python -m tower propose SEC-001
python -m tower inspect
python -m tower approve <full-proposal-hash> --effort-seconds 30
python -m tower execute <full-proposal-hash>
python -m tower status <full-proposal-hash> IN_PROGRESS
python -m tower status <full-proposal-hash> DONE --evidence "Synthetic validation: ingress restriction and rollback checked in fixture"
python -m tower export tower-output
python -m tower verify tower-output/evidence.zip
```

Replace `<full-proposal-hash>` with the 64-character value returned by `propose`.
Approval displays the entire payload and requires typing `APPROVE` plus that full
hash. Approval expires after ten minutes. `reject` works the same way and is terminal.
The program requires a separate `execute` command. Neither this build nor the demo
export automatically approves a proposal. The self-reported effort is active review
time; elapsed time from proposal to decision includes queue time.

The default draft is clearly labeled `reference_fixture`, not AI-generated.
Install `requirements.txt` in a virtual environment for AWS or Bedrock mode.
With separately authorized account access, model use, and spend:

```powershell
python -m tower --profile <temporary-session-profile> --expected-account <account-id> propose SEC-001 --model-id <approved-model-id>
```

The adapter makes one bounded Bedrock Converse call, exposes no tools, rejects
truncated/tool responses and stores text as an unverified draft. The application's
fields and allowed action cannot be changed by model text. Prompt injection may
still influence prose; human review is required. The old evaluation's BLOCKED
decision is not cleared by passing these structural tests. Failures before a draft
is created are CLI errors, not counted in the persisted workflow-command metric.

## Evidence bridges

```powershell
python -m tower import-evidence agentic <run.json> <metadata.json>
python -m tower import-evidence aws-lab <normalized-finding.json> <metadata.json>
```

`metadata.json` is one finding object matching `tower/fixtures.json`; the adapter
replaces its evidence with the original source hash and reference. Supply owner,
category, risk, milestone, due date, dependencies and fixture truth deliberately.
Original agentic snapshot and ticket hashes and templates are validated. The AWS
bridge accepts only `confirmed_sample` GuardDuty records from the lab normalizer;
unconfirmed Security Hub records are rejected. Bridges never import prior approvals
or execute old response actions. They validate structure, not cryptographic source
authenticity. The caller must supply genuinely synthetic metadata and evidence.

Reviewed source baselines:

- Agentic workflow: `3e2afea15fbd6889caa78de305cb872eb1334778`.
- AWS response lab: `6cd1e981768063bb06da30fcae6d399d308956f7`.

The AWS repository remains unchanged; its October 29 teardown is not reversed.

## Program model and controls

Findings are immutable and identified by ID; conflicting reingestion fails.
Missing dependencies and cycles fail. Risk is a transparent likelihood × impact
exercise score (1–25), not an AI inference. Milestones and due dates belong to the
finding. Tickets can be OPEN, IN_PROGRESS, BLOCKED or DONE; closure needs evidence
and all dependencies completed. Closure evidence is operator-attested text, not
independent proof. Revised findings require a new ID and a new approval.

| Category | Illustrative NIST SP 800-53 Rev. 5 controls | Required review |
|---|---|---|
| Public administrative ingress | SC-7, CM-6 | Exposure, restricted ingress, before/after evidence |
| Unpatched component | SI-2, RA-5 | Applicability, patch test, rollback, validation |
| Vendor assurance gap | SR-6, SA-9 | Vendor evidence, gaps, risk-owner disposition |
| Benign comparison | CA-7 | Classification and retained evidence |

Mappings are authored exercise cross-references, not NIST certification, a full
control assessment, or FedRAMP authorization. NIST publishes the authoritative
[control catalog](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final); validate any
real implementation against the applicable catalog release and organizational requirements.

## Storage, evidence and trust

SQLite uses a write transaction across the state, ticket and audit update. DynamoDB
uses a consistent read and version-conditioned whole-document write. Conflicts and
transport errors are not automatically retried: inspect first. A committed ticket
is reconciled by its proposal hash on repeat, even after the original approval
expires. No second external side effect exists. The program is bounded to 300 KB,
so it fails before DynamoDB's item size limit; export and design archival before
larger usage. This is a small program demo, not a high-volume event service.

The operator owns the local database or AWS storage access. Human identity is the
local OS user or the AWS STS ARN, not a caller-supplied name. This is a single-operator
trust model: storage administrators can bypass the CLI, forge approvals or rewrite
the audit chain. Independent approver enforcement and immutable audit storage are
not implemented. The model itself has no storage or approval tools; runtime role
scoping still matters.

Exports contain dashboard HTML, state, metrics, control mapping and a SHA-256
manifest in a ZIP. `verify` checks every file and the audit chain. No signature or
trusted timestamp is claimed; hashes detect corruption, not malicious rewriting
by a privileged operator. Dashboard content is HTML-escaped and has no remote
assets or scripts. It is a generated report; operations happen through the CLI.

## Measurement and limitations

- Detection: category routing versus supplied synthetic ground-truth labels. The
  six development fixtures include TP=3, FP=1, TN=1, FN=1 (accuracy 4/6). This is
  not scanner, AI detection, or held-out production accuracy.
- Reliability: successful persisted workflow commands / persisted attempts;
  intentional denials count as unsuccessful. Transport failures, provider errors
  and aborted CLI confirmations are outside that denominator. This is not uptime.
- Review time: mean proposal-to-decision elapsed seconds, with review count.
- Effort: summed self-reported active review seconds. Savings remain null until a
  comparable measured manual baseline exists. No invented productivity claim.

Run `python -m unittest discover -s tests -p "test_*.py" -v` with repository
dependencies installed. The new suite covers concurrency, rejection, expiry,
tampering, replay, dependency closure, model boundaries and evidence packaging.
AWS DynamoDB concurrency and IAM still require live validation after authorization.
