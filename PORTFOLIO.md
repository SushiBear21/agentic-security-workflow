# Robert Piston — AI Security & Cloud Delivery Portfolio

Security engineering with explicit boundaries, measurable evaluation, and operational handoff.

These four repositories connect AI-assisted analysis to controlled execution and
program oversight. Start with the question that matches your review; each project
links its implementation, evidence, and limitations.

## Choose a project

| Project | Problem addressed | Engineering evidence | Boundary |
| --- | --- | --- | --- |
| [Secure Enterprise RAG](https://github.com/SushiBear21/secure-enterprise-rag) | Answer document questions without exposing restricted evidence | Identity-derived retrieval filters, pre-model access checks, Terraform, recorded employee/SOC evaluations | Synthetic documents; focused sandbox evaluations |
| [AI Cyber Threat Intelligence](https://github.com/SushiBear21/ai-cyber-threat-intel) | Turn vulnerability intelligence into explainable analyst priorities | Deterministic KEV/EPSS scoring, provenance, scheduled AWS processing, reviewed report | Synthetic asset rules; AI commentary needs human review |
| [AWS Security Response](https://github.com/SushiBear21/aws-security-response-lab) | Convert detections into investigated, approved response proposals | Event routing, evidence hashes, payload-bound approval, recorded rollback exercises | Unattached ENI simulation; deployed lab torn down |
| [Agentic Security & Control Tower](README.md) | Bound agent authority and connect findings to decisions, delivery, and executive reporting | Tool restrictions, exact-payload approvals, evaluation gates, dashboards, release rehearsal | Synthetic program; AI-quality decision remains blocked |

## Four delivery capabilities

See [AI operations and assurance evidence](docs/portfolio/ai-capability-evidence.md) for the
versioned release rehearsal, security measurements, governance checks and synthetic delivery metrics.

| Capability | Review first | What the evidence establishes |
| --- | --- | --- |
| Deployment engineering | [Deployment automation](docs/portfolio/deployment-automation.md), [validation](docs/portfolio/completion-validation.md) | Container builds, CI, security scans, SBOMs, approval tests and rollback logic; new ECS staging execution remains pending |
| Federal AI compliance exercise | [Synthetic SSP](docs/portfolio/synthetic-ssp.md), [POA&M](docs/portfolio/poam.json), [monitoring](docs/portfolio/continuous-monitoring.md) | Selected-control mappings and evidence handling; no authorization or full baseline assessment |
| AI Security Program Control Tower | [Design and commands](docs/control-tower.md) | Finding intake, bounded drafting, human decisions, dependency tracking and executive evidence reports |
| Enterprise AI delivery | [Delivery case study](docs/portfolio/ai-program-delivery-case-study.md), [adoption measurement](docs/portfolio/adoption-measurement.md) | Planning, acceptance, risk, handoff and a synthetic adoption measurement framework |

## Evidence worth discussing

- **Authorization before inference:** RAG checks returned evidence before allowing it into model context. [Implementation](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/app/rag_service.py).
- **Approval binds to the action:** changing a proposal invalidates its approval; the model cannot approve or execute it. [Workflow](app/workflow.py).
- **A green test suite is not an AI release decision:** both evaluated configurations passed 36/36 structural checks but only 9/12 human draft reviews against a 12/12 requirement. Both remained blocked. [Decision and limitations](docs/p4-final-results.md).
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
outcomes. New ECS publishing/deployment workflows require environment setup and
live execution. The AI-quality gate remains blocked pending better evidence.

## Implementation map

Python · AWS Bedrock · Terraform · IAM/Cognito · Lambda · EventBridge ·
DynamoDB/SQLite · S3 · GitHub Actions · Docker · Trivy · CycloneDX

See each project's README for its exact stack and supported execution path.
