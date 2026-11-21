# Robert Piston — AI Security & Cloud Delivery Portfolio

Security engineering with explicit boundaries, measurable evaluation, and operational handoff.

These five projects cover AI security, cloud response, program delivery, and
fraud detection. Each project links directly to its README section with the
objective, success criteria, and evidence.

## Project summaries

| Project | Problem addressed | Engineering evidence | Boundary  README evidence |
| --- | --- | --- | --- | --- |
| [Secure Enterprise RAG](https://github.com/SushiBear21/secure-enterprise-rag) | Answer document questions without exposing restricted evidence | Identity-derived retrieval filters, pre-model access checks, Terraform, recorded employee/SOC evaluations | Synthetic documents; focused sandbox evaluations | [Objective, success criteria, and evidence](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/README.md#objective-success-criteria-and-evidence) |
| [AI Cyber Threat Intelligence](https://github.com/SushiBear21/ai-cyber-threat-intel) | Turn vulnerability intelligence into explainable analyst priorities | Deterministic KEV/EPSS scoring, provenance, scheduled AWS processing, reviewed report | Synthetic asset rules; AI commentary needs human review | [Objective, success criteria, and evidence](https://github.com/SushiBear21/ai-cyber-threat-intel/blob/main/README.md#objective-success-criteria-and-evidence) |
| [AWS Security Response](https://github.com/SushiBear21/aws-security-response-lab) | Convert detections into investigated, approved response proposals | Event routing, evidence hashes, payload-bound approval, recorded rollback exercises | Unattached ENI simulation; deployed lab torn down | [Objective, success criteria, and evidence](https://github.com/SushiBear21/aws-security-response-lab/blob/main/README.md#objective-success-criteria-and-evidence) |
| [Agentic Security & Control Tower](README.md) | Bound agent authority and connect findings to decisions, delivery, and executive reporting | Tool restrictions, exact-payload approvals, dashboards, verified live ECS rollback, and an approved Bedrock holdout release | Synthetic program and AWS sandbox | [Objective, success criteria, and evidence](https://github.com/SushiBear21/agentic-security-workflow/blob/main/README.md#objective-success-criteria-and-evidence) |
| [Loyalty Fraud Detection Lab](https://github.com/SushiBear21/loyalty-fraud-detection-lab) | Detect simulated account takeover and miles fraud while limiting customer friction | Explainable review queue, time-based evaluation, and measured fraud capture, friction, and analyst precision | Synthetic events and illustrative loss estimates | [Objective, success criteria, and evidence](https://github.com/SushiBear21/loyalty-fraud-detection-lab/blob/main/README.md#objective-success-criteria-and-evidence) |

**Latest result.** The prospective Bedrock holdout passed all six automated checks. All four drafts passed independent human review, and a human approved the exact release manifest after all five gates passed. [Lab release summary](docs/portfolio/customer-deployment.md#approved-bedrock-holdout-lab-release).

## Cloud and AI governance exercises

The [three exercise walkthroughs](docs/portfolio/cloud-and-ai-governance-drills.md)
cover a multi-account AWS landing zone, selected FedRAMP 20x evidence checks,
and a model change and incident drill. The repository generates reviewable
evidence for the guardrail, remediation retest and model rollback.

## Four delivery capabilities

See [AI operations and assurance evidence](docs/portfolio/ai-capability-evidence.md) for the
versioned release rehearsal, security measurements, governance checks and synthetic delivery metrics.

| Capability | Review first | What the evidence establishes |
| --- | --- | --- |
| Deployment engineering | [Deployment case study](docs/portfolio/customer-deployment.md#live-aws-ecs-rollback-and-human-review--november-17-2026), [deployment automation](docs/portfolio/deployment-automation.md) | Container builds, CI, scans, SBOMs, and verified live ECS sandbox rollback |
| Federal AI compliance exercise | [Synthetic SSP](docs/portfolio/synthetic-ssp.md), [POA&M](docs/portfolio/poam.json), [monitoring](docs/portfolio/continuous-monitoring.md) | Selected-control mappings and evidence handling; no authorization or full baseline assessment |
| AI Security Program Control Tower | [Design and commands](docs/control-tower.md) | Finding intake, bounded drafting, human decisions, dependency tracking and executive evidence reports |
| Enterprise AI delivery | [Delivery case study](docs/portfolio/ai-program-delivery-case-study.md), [adoption measurement](docs/portfolio/adoption-measurement.md) | Planning, acceptance, risk, handoff and a synthetic adoption measurement framework |

## Evidence worth discussing

- **Authorization before inference:** RAG checks returned evidence before allowing it into model context. [Implementation](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/app/rag_service.py).
- **Approval binds to the action:** changing a proposal invalidates its approval; the model cannot approve or execute it. [Workflow](app/workflow.py).
- **Live evaluation and deployment evidence:** The November 17 Bedrock lab recorded 24/24 human-reviewed drafts passing. A separate AWS Fargate sandbox drill injected a failed health check and verified ECS restored revision `:1` to steady state. [Case study](docs/portfolio/customer-deployment.md#live-aws-ecs-rollback-and-human-review--november-17-2026).
- **A security gate caught a real build issue:** container scans blocked vulnerable images; the runtime was updated and pinned without suppressing HIGH/CRITICAL findings. [Validation](docs/portfolio/completion-validation.md).
- **Missing evidence stays missing:** monitoring checks report absent or stale evidence rather than converting it to a compliance pass. [Implementation](tower/compliance.py).

## Review in ten minutes

Follow the [guided walkthrough](docs/portfolio/walkthrough.md). For deeper inspection,
each repository includes architecture, source, test commands and operations notes.

## How to interpret results

**Automated checks** establish behavior for their tested cases. Use the linked
GitHub Actions runs for the revision and date; a passing badge is not proof of
current AWS configuration.

**Recorded AWS exercises** are historical sandbox observations. The RAG and
response repositories preserve their own scopes and dates. The response lab was
torn down on October 29, 2026; the threat-intelligence schedule was recorded disabled.

**Synthetic demonstrations** use fictional data and exercise assumptions. The
SSP/POA&M is not an official submission. Adoption fixtures are not customer
outcomes. The live ECS rollback used the read-only sandbox service, and the
Bedrock outcome supports a lab demonstration.

## Implementation map

Python · AWS Bedrock · Terraform · IAM/Cognito · Lambda · EventBridge ·
DynamoDB/SQLite · S3 · GitHub Actions · Docker · Trivy · CycloneDX

See each project's README for its exact stack and supported execution path.
