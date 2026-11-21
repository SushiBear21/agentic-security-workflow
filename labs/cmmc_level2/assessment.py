"""Synthetic CMMC Level 2 exercise; NOT an assessment or certification."""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
DISCLAIMER = "SYNTHETIC TRAINING LAB — NOT A CMMC ASSESSMENT, CERTIFICATION, OR COMPLIANCE ATTESTATION"

def load():
    framework = json.loads((ROOT / "requirements.json").read_text())
    scenario = json.loads((ROOT / "scenario.json").read_text())
    requirements = framework["requirements"]
    assert len(requirements) == 110
    assert len({r["id"] for r in requirements}) == 110
    assert len({r["family"] for r in requirements}) == 14
    assert scenario["synthetic"] is True
    return requirements, scenario

def build():
    requirements, scenario = load()
    observations = {o["id"]: o for o in scenario["observations"]}
    unknown = set(observations) - {r["id"] for r in requirements}
    if unknown:
        raise ValueError(f"Unknown requirement IDs: {sorted(unknown)}")
    OUT.mkdir(exist_ok=True)
    rows = []
    poam = []
    for r in requirements:
        rid = r["id"]
        observation = observations.get(rid)
        status = observation["result"] if observation else "NOT_EVALUATED"
        reason = observation["reason"] if observation else "No synthetic assessment performed; evidence not collected"
        evidence_id = "SIM-EV-" + rid.replace(".", "-") if observation else ""
        row = {"requirement_id":rid,"cmmc_id":r["cmmc_id"],"family":r["family"],"requirement":r["requirement"],"objective_count":len(r["assessment_objectives"]),"simulation_status":status,"evidence_reference":evidence_id,"evidence_type":"SIMULATED ONLY" if evidence_id else "MISSING","evidence_owner":"Fictional security team","evidence_reviewed":False,"interview_prompt":"Show approved implementation and demonstrate each objective for "+rid+". Who owns it and how is effectiveness verified?","notes":reason}
        rows.append(row)
        if status == "NOT_MET":
            poam.append({"finding_id":"SIM-FI-"+rid.replace(".","-"),"requirement_id":rid,"description":reason,"owner":"Fictional control owner","priority":"Needs triage","milestone":"Design corrective control, implement, independently retest","due_date":"TBD","closure_evidence":"Not collected","status":"OPEN","poam_eligibility":"UNDETERMINED; apply 32 CFR 170.21 eligibility restrictions, never assume conditional status"})
    def write_csv(name, data):
        with (OUT/name).open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    write_csv("evidence_tracker.csv",rows)
    write_csv("poam.csv",poam)
    write_csv("asset_inventory.csv",scenario["assets"])
    write_csv("assessment_interviews.csv",[{"requirement_id":r["requirement_id"],"family":r["family"],"prompt":r["interview_prompt"],"objectives":r["objective_count"]} for r in rows])
    evaluated = [r for r in rows if r["simulation_status"] != "NOT_EVALUATED"]
    counts = {s:sum(r["simulation_status"]==s for r in rows) for s in ("MET","NOT_MET","N/A","NOT_EVALUATED")}
    report = f"""# CMMC Level 2 management exercise — {scenario['name']}

**{DISCLAIMER}**

## Framework and status
CMMC Level 2 maps to 110 NIST SP 800-171 Rev 2 requirements in 14 families, under 32 CFR Part 170. NIST Rev 3 exists but is not substituted for the Rev 2 CMMC baseline. On July 13, 2026, DoD announced a pause in Phase II rollout; Phase I self-assessments remain. Reconfirm rules before any real engagement.

## Fictional scope
{scenario['boundary']}

In-scope and out-of-scope asset classification appears in asset_inventory.csv. An out-of-scope claim requires validation of actual data flow and security protection dependencies. All data and evidence IDs are fictional.

## Simulated observations
- Requirements in catalog: {len(rows)}
- Explicit simulated observations: {len(evaluated)}
- MET: {counts['MET']}; NOT MET: {counts['NOT_MET']}; N/A: {counts['N/A']}
- NOT EVALUATED: {counts['NOT_EVALUATED']}
- Open fictional remediation items: {len(poam)}

**No readiness percentage, certification status, SPRS score, or assessment score is asserted.** Unknown requirements are not MET. The N/A determination is illustrative and requires verification.

## Management decision
**NO-GO for claiming assessment readiness.** Complete evidence collection, boundary validation, objective-level examination/interviews/tests, approved SSP, and remediation. Independent review is required. Do not report synthetic artifacts to SPRS or eMASS.

## Assessment rules and safeguards
- Assessment methods: examine, interview, test per NIST SP 800-171A and official CMMC Assessment Guide.
- MET requires all applicable objectives and final-form evidence. A draft document or lab test is insufficient.
- CMMC weighted scoring starts at 110 and deducts 1/3/5 points per NOT MET requirement, subject to limited partial-credit exceptions. This exercise does not compute a score from incomplete observations.
- Conditional Level 2 POA&Ms are restricted by 32 CFR 170.21 and closeout is due within 180 days; some requirements cannot be placed on qualifying POA&Ms. Ordinary internal remediation tracking is not a substitute.
- Actual Level 2 self-assessment and C3PAO certification paths differ; C3PAO assessment is not performed here.
- Existing security portfolio tests, infrastructure and dashboards are **reusable patterns**, not evidence of this fictional contractor's implemented controls.

## Priority remediation
""" + "\n".join(f"- {p['requirement_id']}: {p['description']} — {p['status']}" for p in poam) + """

## Sources checked
- https://dodcio.defense.gov/CMMC/About/
- https://dodcio.defense.gov/CMMC/Resources-Documentation/
- https://www.ecfr.gov/current/title-32/part-170
- https://doi.org/10.6028/NIST.SP.800-171r2
- https://doi.org/10.6028/NIST.SP.800-171A
"""
    (OUT/"management_report.md").write_text(report,encoding="utf-8")
    ssp = f"""# Synthetic System Security Plan — {scenario['name']}

**{DISCLAIMER}**

## Purpose and boundary
{scenario['boundary']}

## Asset inventory and category rationale
""" + "\n".join(f"- {a['id']} — {a['name']}: {a['category']}; {'included in exercise' if a['in_scope'] else 'excluded from exercise subject to validation'}" for a in scenario["assets"]) + """

## Fictional data flow
Dummy engineering records are viewed on fictional engineering workstation, stored in fictional object storage, protected by fictional key management, and monitored by fictional security telemetry. No real CUI, AWS account, data transfer or cloud deployment exists.

## Roles and responsibilities
Fictional system owner approves scope, fictional security lead owns control narratives, fictional cloud owner maintains configurations, fictional assessor conducts independent examine/interview/test exercises.

## Implementation statements
For all 110 requirements, the evidence tracker records status, assessment objectives, owner, evidence reference, and interview prompt. Unassessed requirements remain NOT_EVALUATED. No control is represented as operational solely because another portfolio project demonstrates a similar pattern.

## Interconnections, inheritance, and exclusions
All third-party services, external connections, security-protection assets and inherited responsibilities require independent verification. No FedRAMP or CMMC authorization is claimed. Public marketing site exclusion is conditional on proving it cannot process, store, transmit CUI or protect in-scope systems.

## Maintenance
Fictional owner must update after material scope/control changes and before any assessment. This document is intentionally incomplete as a real SSP and must not be submitted as evidence of compliance.
"""
    (OUT/"synthetic_ssp.md").write_text(ssp,encoding="utf-8")
    return counts

if __name__ == "__main__":
    print(json.dumps(build(),sort_keys=True))
