# Customer deployment case study: reproducible local acceptance

## Customer problem and boundary

A fictional security team needs advisory findings converted into reviewable,
auditable work without granting AI approval or execution authority.
This is a synthetic delivery exercise, with no actual customer, production
rollout or FedRAMP authorization claim.

The existing Control Tower supplies risk/dependency tracking, SQLite transactions,
DynamoDB conditional writes, ticket approvals and evidence exports. This extension
reuses those components and the existing access simulation and Project 4 context
runner.

## Delivery milestones and acceptance

| Milestone | Acceptance evidence |
| --- | --- |
| Intake and boundaries | Existing synthetic findings validated; unapproved execution denied |
| Operator workflow | Exact-digest simulated review; one ticket despite repeated execution |
| Evidence handoff | Existing evidence ZIP verified; selected-control readiness pack verified |
| Release failure drill | Failed candidate health injected; new local instance restored from SQLite backup; state exactly matches baseline |
| Evaluation | Versioned regression cases, traces, source/dataset hashes, median and nearest-rank p95 |
| Dependency inventory | CycloneDX 1.5 inventory of installed pinned Python application dependencies |
| Readiness decision | Missing evidence and failed human quality block eligibility |

## Reproduce

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python p4_regression.py --output regression.json
python -m tower.release --output release-evidence-new
docker build -t portfolio-rehearsal .
docker run --rm --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m portfolio-rehearsal
```

Use a new output directory. The rehearsal preserves the candidate database,
baseline backup, restored database, dashboard, ZIP, SBOM, access audit,
regression report and assessment/decision JSON. It never replaces a live database.
The container runs as UID 10001, without network and with a read-only root during
the documented run; only temporary outputs are writable.

The rehearsal returns zero when its acceptance checks succeed, even though
readiness remains **blocked**. Inspect `decision.json` before interpreting it.
It does not run unit tests or a vulnerability scanner itself, so those gates stay
unmeasured. The separate CI jobs execute tests, build/run the container and scan
pinned dependencies with pip-audit. Their results must be retained and bound into
a new assessment before counting them as readiness evidence.

## Operational handoff and rollback

1. Preserve the failed candidate and evaluation evidence.
2. Stop the candidate and restore a new isolated instance from the baseline backup.
3. Verify exact restored state and rerun acceptance checks before switching traffic.
4. For a real code release, revert a reviewed commit and rebuild a pinned image;
   the local exercise covers SQLite restore. The separate ECS sandbox drill below covers cloud rollback.
5. Treat a timed-out DynamoDB write as uncertain. Read consistent state before
   retrying; the regression test simulates commit followed by acknowledgement loss.
   Synthetic ticket execution reconciles to one ticket.

Review effort in this drill is synthetic fixture input, not measured human effort.
Offline latency is local reference timing, not Bedrock latency. Model token and cost
fields are null because no model was called. The local fixture rehearsal did not score live model drafts. See the later human review below.

The Python base image is pinned to the digest observed in the hosted build.
For an actual deployment, review/update that digest, scan the OS/image, use
authenticated independent roles and durable protected audit storage.

## Windows Docker Desktop rehearsal results

The offline Docker rehearsal denied unapproved execution and recorded exactly
one ticket. After an injected candidate health-check failure, it restored the
baseline SQLite state and verified an exact match.

The rehearsal passed its acceptance checks. The release decision withheld
production authorization because the dependency-scan and human-quality gates
were unmet.

[Acceptance results](evidence/acceptance.json) · [Release decision](evidence/decision.json)

## Image scan and human-review evidence

The container CI job records the rehearsal image config digest from Docker,
checks that the Trivy JSON names that digest, and includes the report hash in
the assessment. The gate requires OS and library coverage, a report no older
than 24 hours, and zero HIGH or CRITICAL findings. A local offline rehearsal
without scan input leaves the gate unmeasured. The Docker config digest is
distinct from the ECR manifest digest used for staging.

For human review, use a complete live comparison and the exact rehearsal
image ID. Generate the side-by-side packet, then record judgments in the
existing interactive review:

```sh
python p4_review.py --report comparison.json --packet review-packet.json --release-id "$IMAGE_ID"
python p4_review.py --report comparison.json --reviewer "Reviewer name" --release-id "$IMAGE_ID"
```

The packet includes source documents, paired model drafts, and the rubric.
The reviewer records facts and citation support, unsupported claims, and
whether uncertainty is clear. Keep the resulting `human-review.json` beside
the comparison. A release run that supplies both the image scan and the
comparison checks the review's image ID as well as the comparison hash.
The existing evaluator still determines whether any configuration qualifies.

## Live AWS ECS rollback and human review — November 17, 2026

The read-only service ran on AWS Fargate in a sandbox with public IP assignment
disabled. ECR interface endpoints and an S3 gateway endpoint supplied the image
pull path. The drill used the ECS rolling deployment circuit breaker with rollback
enabled.

| Check | Observed result |
| --- | --- |
| Baseline task definition | `portfolio-rollback-drill:1`, rollout `COMPLETED`, one running task and zero pending |
| Candidate task definition | `portfolio-rollback-drill:2`, derived from `portfolio-rollback-drill:1`, with the same immutable ECR image and an injected container health check that exited with code 1 |
| Candidate failure | ECS recorded the deployment failure |
| Rollback | ECS returned to `portfolio-rollback-drill:1` and reached `COMPLETED` with one desired, one running and zero pending tasks |
| Post-drill scale-down | Zero desired, running and pending tasks |

The local evidence file recorded `rollback_verified: true`. This published
summary omits AWS account and resource identifiers and service event payloads.
The drill was run from PowerShell against the sandbox ECS service.

In a separate live Bedrock lab evaluation, the portfolio author reviewed **24
drafts** and recorded **24 passes, zero failures and zero pending**. Both
configurations also met 36 of 36 automated contract checks. The final lab
selection chose `temperature-0.5` based on observed median latency
(615.7 ms compared with 659.6 ms in this run). Eligibility criteria were applied
retrospectively, and the result supports a lab demonstration. The deployment
drill used the read-only service.

For the next run, see the [prospective holdout and lab release protocol](prospective-evaluation.md).
