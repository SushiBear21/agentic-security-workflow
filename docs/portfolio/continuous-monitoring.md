# Evidence collection and monitoring

```sh
python -m tower.compliance --output compliance.json
python -m tower.aws_evidence --expected-account ACCOUNT --region REGION --table TABLE --bucket BUCKET --output aws-private.json
python -m tower.compliance --monitoring-evidence index.json --evidence-root private-evidence --output compliance.json
```

The first command validates the synthetic POA&M and reports missing operational
evidence; exit 2 means monitoring is not ready, not that validation passed.
Exit 0 requires all configured observations to be current and passing.

An index maps each ID from `monitoring-plan.json` to
`{"path":"scan.json","sha256":"...","measured_at":"2026-11-15T12:00:00Z","outcome":"pass"}`.
Supply outcomes only after reviewing the actual artifact. The monitor verifies
path containment, file hashes, aware timestamps and freshness. It cannot prove
that a self-attested passing observation establishes control effectiveness.

The optional AWS collector makes read-only STS, DynamoDB DescribeTable and
S3 configuration calls. It verifies account/table region and sends
ExpectedBucketOwner on S3 reads. It never reads objects or table records.
An account, table or bucket location mismatch stops collection. A configuration
read that fails after the boundary checks is recorded as unverified. Store
outputs privately and keep live resource identifiers out of public commits.
For the offline exercise, see [Synthetic AWS continuous monitoring](aws-conmon-synthetic.md).

GitHub's container-security workflow runs on pushes/PRs, manually, and Mondays
at 13:23 UTC. It refreshes CI/container evidence and retains artifacts 30 days.
This is repository-level monitoring; no AWS scheduled collector has been deployed.
The plan separately requires fresh AWS evidence, human-quality review and
real adoption observations. Configure longer-term private evidence retention and
a responsible reviewer before relying on it operationally.
