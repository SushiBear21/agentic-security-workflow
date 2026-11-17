"""Plan/apply an immutable image update to one existing ECS staging service."""
import argparse
import copy
import json
import re
from pathlib import Path
from app.workflow import digest

TASK_FIELDS = ("family", "taskRoleArn", "executionRoleArn", "networkMode", "containerDefinitions",
               "volumes", "placementConstraints", "requiresCompatibilities", "cpu", "memory",
               "pidMode", "ipcMode", "proxyConfiguration", "inferenceAccelerators",
               "ephemeralStorage", "runtimePlatform")

def service(ecs, config):
    response = ecs.describe_services(cluster=config["cluster"], services=[config["service"]])
    if response.get("failures") or len(response.get("services", [])) != 1:
        raise ValueError("Expected exactly one existing service")
    return response["services"][0]

def plan(ecs, sts, config):
    required = {"account", "region", "cluster", "service", "container", "repository", "image",
                "expected_previous", "task_role_arn", "execution_role_arn"}
    if set(config) != required or any(not isinstance(v, str) or not v for v in config.values()):
        raise ValueError("Exact nonempty deployment configuration required")
    account, region = config["account"], config["region"]
    if not re.fullmatch(r"[0-9]{12}", account) or not re.fullmatch(r"[a-z]{2}-[a-z]+-[0-9]", region):
        raise ValueError("Invalid account/region")
    prefix = f"arn:aws:ecs:{region}:{account}:"
    if not config["cluster"].startswith(prefix + "cluster/") or not config["service"].startswith(prefix + "service/"):
        raise ValueError("Cluster/service must be scoped ARNs")
    repo = config["repository"]
    registry = f"{account}.dkr.ecr.{region}.amazonaws.com/"
    if not repo.startswith(registry) or not re.fullmatch(re.escape(repo) + r"@sha256:[0-9a-f]{64}", config["image"]):
        raise ValueError("Expected immutable image in the configured account/repository")
    if sts.get_caller_identity()["Account"] != account: raise ValueError("Wrong AWS account")
    current = service(ecs, config)
    if current.get("status") != "ACTIVE" or current.get("deploymentController", {}).get("type") != "ECS":
        raise ValueError("Active rolling ECS service required")
    if not 1 <= current.get("desiredCount", 0) <= 2:
        raise ValueError("Staging service must have 1-2 desired tasks")
    if current["taskDefinition"] != config["expected_previous"]:
        raise ValueError("Service changed from expected baseline")
    deployments = current.get("deployments", [])
    if len(deployments) != 1 or deployments[0].get("rolloutState") != "COMPLETED":
        raise ValueError("Stable completed baseline required for rollback")
    task = ecs.describe_task_definition(taskDefinition=current["taskDefinition"])["taskDefinition"]
    if task.get("taskRoleArn", "") != config["task_role_arn"] or task.get("executionRoleArn", "") != config["execution_role_arn"]:
        raise ValueError("Task role boundary mismatch")
    request = {k: copy.deepcopy(task[k]) for k in TASK_FIELDS if k in task}
    matching = [v for v in request["containerDefinitions"] if v["name"] == config["container"]]
    if len(matching) != 1: raise ValueError("Exactly one target container required")
    matching[0]["image"] = config["image"]
    return {"schema_version": 1, "scope": "existing staging ECS service; no infrastructure creation",
            "config": config, "previous_task_definition": current["taskDefinition"],
            "register_request": request, "deployment_circuit_breaker": {"enable": True, "rollback": True}}

def deployment_observation(current):
    return {
        "task_definition": current["taskDefinition"],
        "desired_count": current.get("desiredCount"),
        "running_count": current.get("runningCount"),
        "pending_count": current.get("pendingCount"),
        "deployments": [
            {name: item.get(name) for name in ("id", "status", "taskDefinition", "rolloutState")}
            for item in current.get("deployments", [])
        ],
    }


def completed_revision(current, revision):
    deployments = current.get("deployments", [])
    return (
        current["taskDefinition"] == revision and len(deployments) == 1
        and deployments[0].get("rolloutState") == "COMPLETED"
        and current.get("runningCount") == current.get("desiredCount")
        and current.get("pendingCount") == 0
    )


def apply(ecs, prepared, approved_sha):
    if digest(prepared) != approved_sha: raise ValueError("Approval does not match exact deployment plan")
    config = prepared["config"]
    current = service(ecs, config)
    if current["taskDefinition"] != prepared["previous_task_definition"] or len(current.get("deployments", [])) != 1 or current["deployments"][0].get("rolloutState") != "COMPLETED":
        raise ValueError("Service changed after approval")
    candidate = ecs.register_task_definition(**prepared["register_request"])["taskDefinition"]["taskDefinitionArn"]
    evidence = {"plan_sha256": approved_sha, "previous": prepared["previous_task_definition"],
                "candidate": candidate, "image": config["image"], "status": "pending", "baseline_observation": deployment_observation(current)}
    try:
        ecs.update_service(cluster=config["cluster"], service=config["service"], taskDefinition=candidate,
                           deploymentConfiguration={"deploymentCircuitBreaker": prepared["deployment_circuit_breaker"]})
        ecs.get_waiter("services_stable").wait(cluster=config["cluster"], services=[config["service"]],
                                               WaiterConfig={"Delay": 15, "MaxAttempts": 40})
        after = service(ecs, config)
        evidence["candidate_observation"] = deployment_observation(after)
        if not completed_revision(after, candidate):
            raise RuntimeError("Candidate did not complete successfully")
        evidence["status"] = "deployed"
    except Exception as exc:
        evidence.update(status="failed", error_type=type(exc).__name__)
        # Reconcile uncertain update outcomes before any rollback write.
        try:
            after = service(ecs, config)
            evidence["recovery_observation"] = deployment_observation(after)
            if after["taskDefinition"] == candidate:
                ecs.update_service(cluster=config["cluster"], service=config["service"],
                                   taskDefinition=evidence["previous"])
                ecs.get_waiter("services_stable").wait(cluster=config["cluster"], services=[config["service"]],
                                                       WaiterConfig={"Delay": 15, "MaxAttempts": 40})
                restored = service(ecs, config)
                evidence["restored_observation"] = deployment_observation(restored)
                evidence["rollback"] = "restored" if completed_revision(restored, evidence["previous"]) else "unverified"
            elif after["taskDefinition"] == evidence["previous"]:
                evidence["rollback"] = "baseline_observed" if completed_revision(after, evidence["previous"]) else "unverified"
            else:
                evidence["rollback"] = "concurrent_change_manual_review_required"
        except Exception as recovery:
            evidence["rollback"] = "unverified"
            evidence["rollback_error_type"] = type(recovery).__name__
    return evidence

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True); p.add_argument("--output", required=True)
    p.add_argument("--execute", action="store_true"); p.add_argument("--approved-plan-sha")
    a = p.parse_args()
    config = json.loads(Path(a.config).read_text())
    import boto3
    from botocore.config import Config
    session = boto3.Session(region_name=config["region"])
    sdk = Config(connect_timeout=5, read_timeout=30, retries={"total_max_attempts": 1})
    ecs, sts = session.client("ecs", config=sdk), session.client("sts", config=sdk)
    prepared = plan(ecs, sts, config)
    result = apply(ecs, prepared, a.approved_plan_sha) if a.execute else {"plan": prepared, "plan_sha256": digest(prepared), "status": "planned"}
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"planned", "deployed"} else 1

if __name__ == "__main__": raise SystemExit(main())
