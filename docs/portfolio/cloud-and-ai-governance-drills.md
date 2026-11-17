# AWS organization security and AI governance exercises

These three exercises use synthetic observations, Terraform mock providers,
and a fixture model. The output supports a portfolio walkthrough of security
design, evidence-driven risk decisions, and incident response.

## Reproduce the evidence

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p test_portfolio_drills.py
python -m tower.portfolio_drills --output drill-evidence
terraform -chdir=infra/landing-zone init -backend=false
terraform -chdir=infra/landing-zone validate
terraform -chdir=infra/landing-zone test
```

The evidence generator requires a new output directory. GitHub Actions publishes
the three JSON files. The Terraform tests use mocked providers and plan commands.

## Multi account AWS landing zone

[Terraform design](../../infra/landing-zone/main.tf) expects four logical account
roles inside an existing AWS organization. The management account owns the
multiregion organization trail and an SCP attached to a workload OU. A security
account hosts the organization AWS Config aggregator. A separate log archive
account owns the versioned, encrypted S3 bucket with public access blocked.
Workloads generate the audit events.

The fixture attempts to stop logging from a workload member account and
matches the explicit deny in the checked-in SCP. Its drift exercise compares a
versioning-disabled observation with the expected state, then confirms a
corrected observation matches the baseline. The fixture does not emulate the
entire IAM policy engine or send AWS API requests.

For a real environment, supply distinct organization, security and archive
profiles and a workload OU. Confirm SCPs are enabled, the organization trusts
CloudTrail and Config, Config is recording in the source accounts and regions,
and the security account can aggregate using the supplied role. Review
existing trails, retention, costs, management permissions, and ownership before
creating a real plan. This design expects an existing organization, OUs, and
accounts. The exercise does not create them or apply the configuration.

[Reference AWS landing zone logging design](https://docs.aws.amazon.com/prescriptive-guidance/latest/designing-control-tower-landing-zone/logging.html)

## FedRAMP 20x evidence for a Bedrock service

The boundary includes the illustrative Bedrock application, organization trail,
and log archive. The generated record assigns example provider, customer, and
inherited-service responsibilities. It binds each observation to its evaluation
with a SHA-256 hash and records four states in the evidence lifecycle.

| Selected indicator | Exercise evidence |
| --- | --- |
| KSI-MLA-EVC, Evaluating Configurations | Public access block and archive versioning checks. Disabled versioning fails, and restoration passes the retest |
| KSI-MLA-LET, Logging Event Types | Trail status and a synthetic event-inventory observation. An expired observation fails the freshness check |

The exercise uses a 24-hour freshness rule and fixed synthetic timestamps for
reproducibility. Its JSON is an internal, illustrative Security Decision Record.
These checks cover selected parts of the indicators. Live evidence collection,
formal schema validation, scope and inherited-control review, and a complete
assessment would be separate activities.

[FedRAMP 2026 Class B Key Security Indicators](https://www.fedramp.gov/2026/reference/20x/b/key-security-indicators/)

## AI model change and incident response

The exercise records the stable and candidate model profiles, prompt hash,
impact assessment and fixture release approval. It reuses the existing boundary
regression checks and sends a sample of synthetic requests through the canary.
An invalid advisory output triggers rejection, candidate pause, and fallback.
A fixture incident owner approves continued stable routing after clean
follow-up requests. The candidate stays disabled.

The event journal links preflight, detection, response and recovery with hashes.
It records simulated role decisions and makes zero live model calls. This
exercise complements the separate [approved live Bedrock holdout](customer-deployment.md#approved-bedrock-holdout-lab-release).
