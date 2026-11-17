import copy
import unittest
from unittest.mock import Mock
from app.workflow import digest
from tower.deploy import plan, apply
from tower.service import payload

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.ecs, self.sts = Mock(), Mock()
        prefix = "arn:aws:ecs:us-east-1:123456789012:"
        self.config = dict(account="123456789012", region="us-east-1", cluster=prefix+"cluster/lab",
            service=prefix+"service/lab/tower", container="tower",
            repository="123456789012.dkr.ecr.us-east-1.amazonaws.com/tower",
            image="123456789012.dkr.ecr.us-east-1.amazonaws.com/tower@sha256:"+"a"*64,
            expected_previous=prefix+"task-definition/tower:1",
            task_role_arn="arn:aws:iam::123456789012:role/lab-task",
            execution_role_arn="arn:aws:iam::123456789012:role/lab-execution")
        self.sts.get_caller_identity.return_value = {"Account": "123456789012"}
        self.current = {"status":"ACTIVE", "deploymentController":{"type":"ECS"}, "desiredCount":1, "runningCount":1, "pendingCount":0,
                        "taskDefinition":self.config["expected_previous"], "deployments":[{"rolloutState":"COMPLETED"}]}
        self.ecs.describe_services.return_value = {"services":[self.current]}
        self.ecs.describe_task_definition.return_value = {"taskDefinition":{"family":"tower", "containerDefinitions":[{"name":"tower","image":"old","environment":[{"name":"KEEP","value":"yes"}]}],
             "taskRoleArn":self.config["task_role_arn"], "executionRoleArn":self.config["execution_role_arn"]}}
        self.candidate = prefix+"task-definition/tower:2"
        self.ecs.register_task_definition.return_value = {"taskDefinition":{"taskDefinitionArn":self.candidate}}
    def test_plan_only_changes_image(self):
        result = plan(self.ecs,self.sts,self.config)
        container = result["register_request"]["containerDefinitions"][0]
        self.assertEqual(container["image"],self.config["image"])
        self.assertEqual(container["environment"],[{"name":"KEEP","value":"yes"}])
        self.ecs.register_task_definition.assert_not_called()
        self.ecs.update_service.assert_not_called()
    def test_wrong_account_and_mutable_image_blocked(self):
        self.sts.get_caller_identity.return_value = {"Account":"000000000000"}
        with self.assertRaises(ValueError): plan(self.ecs,self.sts,self.config)
        self.sts.get_caller_identity.return_value = {"Account":"123456789012"}
        self.config["image"] = self.config["repository"]+":latest"
        with self.assertRaises(ValueError): plan(self.ecs,self.sts,self.config)
    def test_wrong_approval_and_drift_block_all_writes(self):
        p = plan(self.ecs,self.sts,self.config)
        with self.assertRaises(ValueError): apply(self.ecs,p,"wrong")
        self.current["taskDefinition"]="other"
        with self.assertRaises(ValueError): apply(self.ecs,p,digest(p))
        self.ecs.register_task_definition.assert_not_called()
    def test_success_checks_actual_candidate(self):
        p = plan(self.ecs,self.sts,self.config)
        after = dict(self.current,taskDefinition=self.candidate)
        self.ecs.describe_services.side_effect=[{"services":[self.current]},{"services":[after]}]
        self.assertEqual(apply(self.ecs,p,digest(p))["status"],"deployed")
    def test_failure_rolls_back_and_retains_failure(self):
        p = plan(self.ecs,self.sts,self.config)
        after = dict(self.current,taskDefinition=self.candidate)
        self.ecs.describe_services.side_effect=[{"services":[self.current]},{"services":[after]},{"services":[self.current]}]
        self.ecs.get_waiter.return_value.wait.side_effect=[TimeoutError("candidate timeout"),None]
        result=apply(self.ecs,p,digest(p))
        self.assertEqual(result["status"],"failed"); self.assertEqual(result["rollback"],"restored")
        self.assertEqual(result["restored_observation"]["running_count"], 1)
        self.assertEqual(self.ecs.update_service.call_args.kwargs["taskDefinition"],self.config["expected_previous"])
    def test_concurrent_change_not_overwritten(self):
        p=plan(self.ecs,self.sts,self.config)
        self.ecs.update_service.side_effect=TimeoutError()
        self.ecs.describe_services.side_effect=[{"services":[self.current]},{"services":[dict(self.current,taskDefinition="other")]}]
        self.assertEqual(apply(self.ecs,p,digest(p))["rollback"],"concurrent_change_manual_review_required")
        self.assertEqual(self.ecs.update_service.call_count,1)
    def test_synthetic_health_and_metrics(self):
        self.assertEqual(payload("/health")[0],200)
        self.assertTrue(payload("/metrics")[1]["synthetic"])
        self.assertEqual(payload("/private")[0],404)
