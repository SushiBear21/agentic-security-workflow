"""Synthetic NIST AI RMF evidence pack and deterministic fail-closed release gate.

Independent training lab, not a commercial assessment, deployment or authorization.
"""
import argparse
import hashlib
import json
from pathlib import Path
from app.workflow import digest
from tower.mcp_identity_lab import demonstration

LAB = "INDEPENDENT SYNTHETIC PORTFOLIO LAB — NOT COMMERCIAL GOVERNANCE OWNERSHIP OR PRODUCTION AUTHORIZATION"
FRAMEWORK = "NIST AI RMF 1.0 (AI 100-1)"
AS_OF = "2026-11-21T18:00:00Z"  # fixed authored fixture time, not live measurement
MAPPING = [
    {"function": "GOVERN", "subcategory": "GOVERN 1.1", "artifact": "system_card.json", "control": "Document obligations and scope"},
    {"function": "GOVERN", "subcategory": "GOVERN 1.3", "artifact": "evaluation_criteria.json", "control": "Declare release thresholds"},
    {"function": "GOVERN", "subcategory": "GOVERN 1.4", "artifact": "risk_register.json", "control": "Assign risks and mitigations"},
    {"function": "GOVERN", "subcategory": "GOVERN 2.1", "artifact": "approval_decision.json", "control": "Separate reviewer and approver"},
    {"function": "MAP", "subcategory": "MAP 1.1", "artifact": "system_card.json", "control": "Intended use and boundaries"},
    {"function": "MAP", "subcategory": "MAP 2.1", "artifact": "risk_register.json", "control": "Threat inventory"},
    {"function": "MAP", "subcategory": "MAP 5.1", "artifact": "system_card.json", "control": "Stakeholders and limitations"},
    {"function": "MEASURE", "subcategory": "MEASURE 1.1", "artifact": "evaluation_criteria.json", "control": "Predefined evaluation"},
    {"function": "MEASURE", "subcategory": "MEASURE 2.1", "artifact": "evaluation_results.json", "control": "Executed fixture tests"},
    {"function": "MEASURE", "subcategory": "MEASURE 3.1", "artifact": "monitoring.json", "control": "Monitoring metrics"},
    {"function": "MANAGE", "subcategory": "MANAGE 1.1", "artifact": "release_decision.json", "control": "Release decision"},
    {"function": "MANAGE", "subcategory": "MANAGE 2.1", "artifact": "risk_register.json", "control": "Risk treatment"},
    {"function": "MANAGE", "subcategory": "MANAGE 4.1", "artifact": "monitoring.json", "control": "Alert and incident response"},
]
SYSTEM_CARD = {
    "synthetic": True, "system": "Fictional Security Finding Draft Assistant / Bounded Action Workflow",
    "model_card": {"model": "No live model called in this package", "provider": "Unspecified; Bedrock labs remain separate",
      "version": "not evaluated", "architecture": "retrieval-assisted advisory draft + bounded local tools",
      "training_data": "no training or fine-tuning", "validation_context": "offline fixtures only"},
    "intended_use": "Analyst-reviewed fictional security summaries and controlled in-memory ticket proposals",
    "users": ["fictional analyst", "fictional risk owner", "fictional independent reviewer"],
    "not_for": ["automatic incident response", "real CUI", "employment decisions", "production authorizations",
                "personal data", "unreviewed privilege escalation"],
    "boundaries": {"data": "dummy synthetic records", "tools": "read fixture/create in-memory ticket",
                   "cloud": "no AWS or Azure", "model": "no inference performed"},
    "human_in_the_loop": "Distinct out-of-band actor must approve exact tool request",
    "known_limitations": ["no authenticated external identity provider", "no real independent reviewer sign-off",
       "no live model holdout in this package", "no verified image or dependency vulnerability scan"],
    "reused_patterns": ["app/workflow.py exact-payload digest",
      "tower/access_demo.py principal roles and maximum credential TTL",
      "secure-enterprise-rag/app/authorization.py audience restriction design",
      "secure-enterprise-rag/tests/security/test_retrieval_boundary.py pre-model access denial"],
}
RISK_REGISTER = [
  {"id": "AI-R01", "risk": "Unauthorized retrieval/CUI leakage", "owner": "Fictional RAG security lead", "severity": "high", "status": "open",
   "mitigation": "Verified-group authorization, pre-model audience check", "evidence_needed": "Deployment access test", "rmf": ["MAP 2.1","MANAGE 2.1"]},
  {"id": "AI-R02", "risk": "Prompt-injected content drives tools", "owner": "Fictional AI security lead", "severity": "high", "status": "open",
   "mitigation": "Server-enforced permissions and exact tool approval", "evidence_needed": "Model red-team", "rmf": ["MAP 2.1","MEASURE 2.1"]},
  {"id": "AI-R03", "risk": "Incorrect or unsupported AI draft", "owner": "Fictional evaluation lead", "severity": "high", "status": "open",
   "mitigation": "Prospective holdout with independent source-based human review", "evidence_needed": "Raw reviewed holdout", "rmf": ["MEASURE 2.1","GOVERN 1.4"]},
  {"id": "AI-R04", "risk": "Replayed or overprivileged tool call", "owner": "Fictional IAM lead", "severity": "high", "status": "mitigated_in_fixture_only",
   "mitigation": "Signed scoped TTL, server ACL, one-time digest-bound approval", "evidence_needed": "Identity provider deployment review", "rmf": ["GOVERN 1.4","MANAGE 2.1"]},
  {"id": "AI-R05", "risk": "Undetected quality drift", "owner": "Fictional SRE lead", "severity": "medium", "status": "open",
   "mitigation": "Threshold-based monitoring, rollback, incident response", "evidence_needed": "Real telemetry", "rmf": ["MEASURE 3.1","MANAGE 4.1"]},
  {"id": "AI-R06", "risk": "Unscanned software and dependencies", "owner": "Fictional DevSecOps lead", "severity": "high", "status": "open",
   "mitigation": "Fresh digest-bound image and library scan", "evidence_needed": "Actual CI vulnerability scan", "rmf": ["GOVERN 1.4","MANAGE 1.1"]},
]
EXPECTED = {"allowed_read":"ALLOW", "denied_wrong_role":"DENY","expired_credential":"DENY",
            "unapproved":"DENY","approved":"ALLOW","replayed_approval":"DENY"}
EVALUATION_CRITERIA = {
  "synthetic":True, "revision":"predeclared-v1", "method":"Local deterministic fixture (zero model calls)",
  "tests": list(EXPECTED), "pass_threshold":"Six of six expected decisions; credentials absent from audit",
  "live_model_holdout":"UNKNOWN, historical repository 6/6 not independently verified here",
  "human_review":"UNKNOWN, historical repository 4/4 not independently verified here",
  "security_scan":"Requires fresh scan on candidate digest with zero HIGH or CRITICAL",
  "monitoring":{"max_failure_rate":0.05,"max_unauthorized_actions":0,"max_alert_age_hours":24},
  "release_rule":"Require every gate, accepted high risks, no open alert, valid exact-manifest independent human approval"
}

def evaluate_offline(mcp_report):
    cases=[{"case_id":name,"expected":expect,"actual":mcp_report["observations"][name]["outcome"],
            "pass":mcp_report["observations"][name]["outcome"]==expect, "model_calls":0,
            "evidence_type":"executed harmless MCP fixture"} for name,expect in EXPECTED.items()]
    return {"synthetic":True,"run_kind":"local authorization fixtures","model_calls":0,
      "passed":sum(x["pass"] for x in cases),"total":len(cases),"cases":cases,
      "audit_secret_scan":{"checks":"Credential values absent from serialized audit","manual_review_required":True},
      "reference_only":{"holdout_6_of_6":"Repository narrative exists; raw primary evidence NOT verified by this package",
        "independent_review_4_of_4":"Repository narrative exists; original signed reviewer artifacts NOT verified by this package"}}

def monitoring():
    sample={"synthetic":True,"clock":AS_OF,"sample_count":100,"request_failures":8,
      "unauthorized_tool_executions":0,"review_backlog":3,"age_hours":1}
    rate=sample["request_failures"]/sample["sample_count"]
    alerts=[]
    if rate > EVALUATION_CRITERIA["monitoring"]["max_failure_rate"]:
        alerts=[{"id":"AL-01","condition":"failure rate above 5%","observed":rate,"open":True,
          "owner":"Fictional SRE lead","action":"Hold release and retest"}]
    return {"synthetic":True,"measurements":sample,"failure_rate":rate,
      "thresholds":EVALUATION_CRITERIA["monitoring"],"alerts":alerts,
      "source":"AUTHORED FIXTURE, not operational telemetry"}

def decision(gates,risk_register,alerts,approval=None):
    required=("offline_tests","model_holdout","independent_review","security_scan","monitoring_fresh","identity_audit")
    verified={k:gates.get(k) is True for k in required}
    high=sorted(r["id"] for r in risk_register if r.get("severity")=="high" and r.get("status")!="accepted")
    open_alerts=sorted(a["id"] for a in alerts if a.get("open"))
    manifest_hash=digest({"gates":verified,"open_high":high,"alerts":open_alerts})
    valid=bool(approval and approval.get("decision")=="approve" and
      approval.get("manifest_sha256")==manifest_hash and approval.get("approver") and
      approval.get("approver")!=approval.get("evaluation_owner") and
      approval.get("independent_identity_verified") is True)
    failed=[k for k,v in verified.items() if not v]
    if high:failed.append("unaccepted_high_risk")
    if open_alerts:failed.append("open_monitoring_alert")
    if not valid:failed.append("independent_exact_manifest_approval")
    return {"synthetic":True,"release_status":"NO_GO" if failed else "LAB_GO",
      "failed_gates":failed,"gates":verified,"open_high_risks":high,"alerts":open_alerts,
      "approval_valid":valid,"manifest_sha256":manifest_hash,"production_authorized":False,
      "certification_or_commercial_claim":False}

def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def build(output):
    out=Path(output)
    if out.exists():raise ValueError("Use new directory; do not overwrite evidence")
    mcp=demonstration()
    evaluation=evaluate_offline(mcp)
    monitor=monitoring()
    passed=evaluation["passed"]==evaluation["total"]
    gates={"offline_tests":passed,"model_holdout":False,"independent_review":False,
      "security_scan":False,"monitoring_fresh":False,"identity_audit":passed}
    release=decision(gates,RISK_REGISTER,monitor["alerts"])
    docs={
      "system_card.json":SYSTEM_CARD,"risk_register.json":RISK_REGISTER,
      "rmf_mapping.json":MAPPING,"evaluation_criteria.json":EVALUATION_CRITERIA,
      "evaluation_results.json":evaluation,"mcp_identity_audit.json":mcp,
      "monitoring.json":monitor,"release_decision.json":release,
      "scan_results.json":{"synthetic":True,"scanner_executed":False,"status":"NOT_VERIFIED",
        "high":None,"critical":None,"exact_image_sha256":None,
        "instructions":"Run CI vulnerability scanner; attach raw exact-image report"},
      "approval_decision.json":{"synthetic":True,"type":"fictional governance board",
        "decision":"WITHHELD","approver":"NO HUMAN APPROVER ACTED",
        "reason":"Unverified gates","independent_identity_verified":False}
    }
    out.mkdir(parents=True)
    for name,data in docs.items():
        (out/name).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    files=[{"file":name,"sha256":sha256_file(out/name),"synthetic":True} for name in sorted(docs)]
    (out/"evidence_manifest.json").write_text(json.dumps({"synthetic":True,"artifact_count":len(files),
      "artifacts":files,"framework":FRAMEWORK,"reference_date":AS_OF,"scope":LAB},indent=2)+"\n")
    report=f"""# Synthetic AI Governance Go/No-Go Report

**{LAB}**

System: {SYSTEM_CARD['system']}. Framework: {FRAMEWORK}.

## Outcome: {release['release_status']} — production authorization: FALSE

Executed local MCP fixture tests: {evaluation['passed']}/{evaluation['total']}. Zero live model calls.
These six tests are NOT the historic Bedrock 6/6 holdout. Prior 4/4 independent
human reviews have not been independently verified for this package.

Failing release gates: {', '.join(release['failed_gates'])}.
Open synthetic monitoring alerts: {len(monitor['alerts'])}.
Unaccepted high-severity risks: {', '.join(release['open_high_risks'])}.

No real security scanner was run by the package builder. No real human reviewed
or approved this release. External model evaluations, vulnerabilities, and
operational monitoring remain UNVERIFIED.

## Management action
Withhold release. Independently review raw model holdout evidence, obtain exact-
revision vulnerability scan, close or formally accept risks, demonstrate real
monitoring, and obtain independently authenticated exact-manifest approval.
No artifact grants actual deployment authority.

## Traceability
See rmf_mapping.json, evidence_manifest.json, mcp_identity_audit.json and
release_decision.json. All inputs and measurements are synthetic or clearly unknown.
"""
    (out/"MANAGEMENT_REPORT.md").write_text(report,encoding="utf-8")
    return {"path":str(out),"decision":release["release_status"],
      "offline_tests":f"{evaluation['passed']}/{evaluation['total']}",
      "manifest":str(out/"evidence_manifest.json")}

def main():
    p=argparse.ArgumentParser(description=LAB)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(build(args.output),sort_keys=True))

if __name__=="__main__":
    main()
