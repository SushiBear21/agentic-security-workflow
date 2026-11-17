# Staging delivery automation and rollback

The source-to-image and image-to-service workflows are implemented. **They have
not deployed AWS resources.** They require an existing private ECS service, ECR
repository and approved OIDC roles. The workload is a read-only synthetic metrics
service, not a production AI application. The AI-quality decision stays blocked.

## Pipeline

1. PR CI builds both Dockerfiles, produces OS/library CycloneDX SBOMs, scans with
   pinned Trivy, and blocks HIGH/CRITICAL vulnerabilities including unfixed ones.
   It also runs tests and a network-isolated service smoke test.
2. After merge, manually run **Build scan and publish staging image**.
   It tests, builds, scans and publishes the same service image to the configured
   ECR repository. Retain the immutable digest from `published-image.txt`.
3. Run **Plan or deploy existing ECS staging service** with action `plan` and
   that digest. Inspect its account, region, service, roles, previous revision,
   proposed task definition and `plan_sha256` artifact.
4. Run it again with action `deploy` and the reviewed `approved_plan_sha`.
   The script reconstructs the plan and refuses a mismatched digest or changed
   baseline. It updates one container image, leaving the remaining task settings.
5. The script waits for stability and verifies that the candidate revision
   completed. AWS circuit-breaker rollback is enabled. On failure, it reconciles
   the observed service before attempting a return to the previous revision.
   Failures remain failures even when recovery succeeds.

## Required environment configuration

Create protected GitHub environment `portfolio-staging`; allow main only, require
an independent reviewer and prevent self-review. Repository files cannot enforce
these settings. Do not grant the roles until the environment protections exist.

Set these environment variables:

| Variable | Value to supply |
| --- | --- |
| AWS_ACCOUNT_ID / AWS_REGION | Approved staging account and region |
| AWS_PUBLISH_ROLE_ARN | OIDC role allowed to push only the chosen ECR repository |
| AWS_DEPLOY_ROLE_ARN | OIDC role allowed to update only the chosen ECS service |
| ECR_REPOSITORY_URI | Existing account/region registry plus repository path |
| ECS_CLUSTER_ARN / ECS_SERVICE_ARN | Existing private staging cluster/service |
| ECS_CONTAINER | Target container name, normally tower |
| ECS_PREVIOUS_TASK_DEFINITION | Last verified stable revision ARN |
| ECS_TASK_ROLE_ARN / ECS_EXECUTION_ROLE_ARN | Exact existing task and execution roles |

Trust only OIDC audience `sts.amazonaws.com` and subject
`repo:SushiBear21/agentic-security-workflow:environment:portfolio-staging`.
Use separate publish/deploy roles. Scope ECR pushes/pulls to the repository,
ECS updates to the service, and iam:PassRole to the two named roles with
iam:PassedToService=ecs-tasks.amazonaws.com. Restrict registration to the intended
task family where supported. Describe/list/get-token operations may need broader
read scope; document that separately. No AdministratorAccess is needed.

The existing service must have 1–2 desired tasks, rolling ECS deployment control,
a completed stable baseline, private networking and appropriate logging/health
checks. Set health endpoint `/health` on port 8080. The demo service has no
authentication and must not be placed on a public listener. Keep the existing
application task role minimal: the read-only synthetic service makes no AWS calls.

## Recovery limits and handoff

GitHub concurrency serializes this workflow, but does not lock out other AWS
operators. Use a change window. If another revision appears after an uncertain
write, the script stops rather than overwrite it. If rollback cannot be verified,
retain the artifact and inspect ECS events/tasks before further action.
Task-definition registration can leave an unused revision on failure; review
and deregister it separately after confirming no service uses it.

No arbitrary shell command or mutable image tag is accepted for deployment.
Targets come from the protected environment; immutable images must be in the
configured ECR repository. Before first execution, review costs, networking,
health checks, role policies and retention for the existing staging environment.

References: [ECS deployment circuit breaker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html),
[Trivy container scans](https://trivy.dev/docs/latest/target/container_image/).

## Evidence to retain for a staging run

Download the deployment artifact after the approved run. Inspect the image,
plan hash, baseline revision, and candidate observation in
`deployment-result.json`. A completed observation requires one completed
deployment, running tasks equal to desired tasks, and zero pending tasks.
For a failed candidate, use the recovery or restored observation to verify
the previous revision reached that same state. Retain the failure result and
the scan alongside the plan. A separately approved staging failure rehearsal
is needed to collect live rollback evidence.
