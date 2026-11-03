# AWS deployment and review plan

Status: storage deployed and bounded synthetic smoke tests passed on November 3,
2026, after explicit approval targeting no more than $1/month. The existing
`portfolio-sandbox` SSO session was refreshed; no persistent credentials or IAM
grants were created. No model calls or infrastructure remediation were performed.

## Observed deployment

- Account/region: `359769212511`, `us-east-1`.
- Stack: `portfolio-security-control-tower`, status `CREATE_COMPLETE`.
- Resources: one on-demand DynamoDB table, one private S3 bucket and its TLS-only
  bucket policy. The change set contained exactly these three additions.
- Table: `portfolio-security-control-tower-Program-6DIHL744X3DD`.
- Bucket: `portfolio-security-control-tower-evidence-dvugfrgx2i1h`.
- Six synthetic findings ingested; duplicate intake and proposals reused the same
  records. Three proposals are PENDING, with zero tickets and zero approvals.
- Attempted execution of a PENDING proposal was denied and audited.
- Bucket public-access block, nonpublic policy status, AES256 encryption and
  versioning were verified using AWS read APIs. TLS-only denial was inspected in
  the bucket policy, not tested by sending an insecure request.
- One evidence ZIP was uploaded, retrieved by version ID, compared byte-for-byte,
  and passed manifest/audit-chain verification after download.

This was operated using the existing AdministratorAccess SSO role. Least-privilege
runtime access, independent approver identity, approved live execution, expiry and
live concurrency were not validated; those remain separate from offline tests.
The generated dashboard stays local; no public website was deployed.

## Cost and retention status

The authorized target is no more than $1/month. Illustrative tiny storage-only
usage is about $0.05/month (100 writes and 200 strong reads at the 300 KB document
limit, 1 GB S3 storage, 100 uploads). This is an estimate, not observed billing,
and excludes model calls, downloads, taxes and unrelated account services.
AWS billing has not yet established project-attributed cost. No background jobs
or model calls are enabled. The existing account budget is $10/month; a separate
$1 project alert or hard cap has not been configured. Budget alerts are not caps.

Storage remains live for the demo. Stack deletion retains the table and bucket,
including evidence versions, so storage billing continues until retained resources
are explicitly removed. No existing lab resources were changed or cleaned up.

Initial sandbox checks returned NoCredentials; inspection through the user's
existing profile later found an expired SSO session. Those earlier access blockers
are resolved. Historical preparation guidance follows.

## Proposed footprint

`infra/control-tower.json` creates one on-demand DynamoDB table, one private,
encrypted/versioned S3 evidence bucket and a TLS-only bucket policy. It creates no
IAM roles, public website, model endpoint, scheduled job, Lambda, EC2 or live
remediation integration. The dashboard runs locally; the optional S3 upload stores
its evidence ZIP privately. All cloud resources carry the project tag.

Both storage resources are retained on stack deletion to avoid accidental loss.
Retention means storage charges can continue after stack deletion. There is no
automatic lifecycle deletion. Request and storage usage may incur charges; Bedrock
has separate model/token charges. This implementation makes no free-tier or fixed
cost claim. Approve account, region, service footprint, spending ceiling and
retention period before deployment or a model call. Inspect current pricing and
existing budget alarms in that account; budget alerts are not hard spending caps.

## Preflight and approval

1. Use an existing short-lived SSO session, without exporting or creating persistent
   credentials. Confirm STS account and role and region. Do not reuse the old lab's
   administrator identity as proof of least privilege.
2. Inventory the existing lab stack, retained evidence/state, OIDC role and budget
   configuration. Do not overwrite or attach this module to those resources.
3. Validate the template using CloudFormation and review a create change set named
   for a new `portfolio-security-control-tower` stack. This must show only the three
   resources above. Do not execute a change set until spending is approved.
4. Supply actual stack output ARNs to `operator-policy.example.json`. It scopes
   GetItem/PutItem to one table and PROGRAM partition and S3 PutObject to the
   evidence prefix. It is an unattached policy example, not an access grant.
   Have the account owner review a temporary session role. No List/Scan/Delete,
   EC2, IAM, Secrets Manager or model permissions are needed for storage mode.
5. Optional model invocation requires a separate reviewed `bedrock:InvokeModel`
   grant limited to the approved model ARN (and any specifically required inference
   profile resources). No wildcard model permission is supplied. Do not accept
   model marketplace terms or subscribe automatically.

## Deployment commands after approval

Use the selected temporary profile and region for all AWS commands. First validate:

```powershell
aws cloudformation validate-template --template-body file://infra/control-tower.json --profile <profile> --region <region>
aws cloudformation create-change-set --stack-name portfolio-security-control-tower --change-set-name initial-review --change-set-type CREATE --template-body file://infra/control-tower.json --profile <profile> --region <region>
aws cloudformation describe-change-set --stack-name portfolio-security-control-tower --change-set-name initial-review --profile <profile> --region <region>
```

Execute only the reviewed change set after the account/spend decision. No automatic
apply workflow is added to GitHub. Obtain the table and bucket from stack outputs.

```powershell
python -m tower --profile <profile> --region <region> --expected-account <account> --table <table> ingest tower/fixtures.json
python -m tower --profile <profile> --region <region> --expected-account <account> --table <table> propose SEC-001
python -m tower --profile <profile> --region <region> --expected-account <account> --table <table> inspect
```

Repeat the same global AWS options for `approve`, `execute`, `status` and `export`.
For export add `--bucket <bucket>` after its output directory. A content-hash S3
object key and conditional PutObject prevent silent overwrite; if an upload has
an uncertain outcome, inspect the exact key before retrying. No bucket policy
makes it public. Downloading evidence requires a separately scoped read permission.

## Required live acceptance and rollback

Verify: wrong account denial, non-synthetic rejection, exact approval hash, expired
decision denial, 16 concurrent requests creating one ticket or returning explicit
conditional conflicts, replay reconciliation, private bucket/TLS enforcement,
evidence download hash verification and attributable cost observation. Record
actual results separately from offline unit tests. Test temporary role permissions
and absence of unrelated access. Do not claim independent separation of duties.

If verification fails, stop writes and export the state. There is no cloud-resource
remediation to roll back. Remove temporary role access only after evidence handling
is complete. Stack deletion retains the table/bucket; any later permanent deletion
needs explicit review of backups, versions and retention needs. Observe charges
until retained storage is removed or accepted for continued retention.

References: [DynamoDB conditional writes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html),
[Bedrock Converse](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html).
