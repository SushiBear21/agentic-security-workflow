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
   this exercise does not implement traffic switching, cloud rollback or schema migration.
5. Treat a timed-out DynamoDB write as uncertain. Read consistent state before
   retrying; the regression test simulates commit followed by acknowledgement loss.
   Synthetic ticket execution reconciles to one ticket.

Review effort in this drill is synthetic fixture input, not measured human effort.
Offline latency is local reference timing, not Bedrock latency. Model token and cost
fields are null because no model was called. The existing failed human-quality
evaluation remains authoritative.

The Python base image is pinned to the digest observed in the hosted build.
For an actual deployment, review/update that digest, scan the OS/image, use
authenticated independent roles and durable protected audit storage.
