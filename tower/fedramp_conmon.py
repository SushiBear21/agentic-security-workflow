"""Offline AWS-only FedRAMP-inspired ConMon exercise; never an authorization decision.

This generator reads local synthetic fixtures and source files. It never invokes
the separate read-only AWS collector or consumes its live snapshots.
"""
import argparse
import hashlib
import html
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from tower.aws_evidence import OBSERVATION_NAMES
from tower.readiness_package import ROOT, digest, safe_relative

FIXTURE = ROOT / "tests/fixtures/conmon-aws-v1.json"
SEVERITIES = ("critical", "high", "moderate", "low")
STATUSES = ("open", "in_progress", "closed")
# Educational local policy, NOT FedRAMP-mandated remediation limits.
DEMO_SLA_DAYS = {"critical": 2, "high": 7, "moderate": 30, "low": 90}
OUTPUTS = ("monthly-report.json", "poam.json", "control-mappings.json",
           "evidence-index.json", "ssp.json", "dashboard.html")
DISCLAIMER = (
    "SYNTHETIC PORTFOLIO EXERCISE ONLY; no FedRAMP authorization, "
    "certification, 3PAO assessment, live scan, continuous monitoring "
    "service, NIST control satisfaction, or production SLA claim."
)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n")


def checked_date(value):
    if not isinstance(value, str):
        raise ValueError("Expected ISO date")
    return date.fromisoformat(value)


def source_inventory(root, mapping):
    """Hash allowed local sources; a source file is NOT proof a control works."""
    root = Path(root).resolve()
    inventory = {}
    for row in mapping:
        for name in row["evidence"]:
            path = root / safe_relative(name)
            if not path.resolve().is_relative_to(root) or path.is_symlink():
                raise ValueError("Unsafe source evidence")
            if name not in inventory:
                inventory[name] = {
                    "status": "source_present" if path.is_file() else "missing",
                    "sha256": digest(path) if path.is_file() else None,
                    "assurance": "source_file_only_not_control_assessment",
                }
    return dict(sorted(inventory.items()))


def summarize_observations(fixture):
    observations = fixture.get("aws_observations")
    if not isinstance(observations, dict) or set(observations) != OBSERVATION_NAMES:
        raise ValueError("Expected the complete synthetic AWS observation set")
    if any(status not in ("collected", "unverified") for status in observations.values()):
        raise ValueError("Invalid synthetic AWS observation status")
    return {
        "synthetic": True,
        "mode": "fixture_only",
        "region": fixture["aws_region"],
        "observations": observations,
        "counts": dict(sorted(Counter(observations.values()).items())),
    }


def remediation_retest(finding, discovered, closed_at, evidence):
    """Validate two synthetic observations; emit IDs, outcomes and digests."""
    pair = finding.get("retest")
    if not closed_at or not isinstance(pair, dict) or set(pair) != {"before", "after"}:
        raise ValueError("SI-2 closure requires before/after fixture retest evidence")

    observations = []
    times = []
    for stage, confirmed in (("before", False), ("after", True)):
        sample = pair[stage]
        if (not isinstance(sample, dict)
                or set(sample) != {"id", "observed_at", "remediation_confirmed"}
                or sample["remediation_confirmed"] is not confirmed):
            raise ValueError("Fixture retest must show remediation confirmation fail then pass")
        evidence_id = sample["id"]
        if (not isinstance(evidence_id, str) or not evidence_id.strip()
                or evidence_id in evidence or evidence_id == finding["id"]
                or (observations and evidence_id == observations[0]["id"])):
            raise ValueError("Distinct fixture retest evidence IDs required")
        timestamp = sample["observed_at"]
        if not isinstance(timestamp, str) or "T" not in timestamp or not timestamp.endswith("Z"):
            raise ValueError("Fixture retest timestamps must be UTC")
        try:
            times.append(datetime.fromisoformat(timestamp))
        except ValueError as exc:
            raise ValueError("Invalid fixture retest timestamp") from exc
        record = {
            "id": evidence_id, "finding_id": finding["id"], "asset_id": finding["asset_id"],
            "control": finding["control"], "stage": stage, "observed_at": timestamp,
            "check": "fixture_remediation_confirmation", "expected": True, "observed": confirmed,
            "outcome": "pass" if confirmed else "fail", "synthetic": True,
        }
        observations.append({**record, "sha256": hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()})
    if not discovered <= times[0].date() or not times[0] < times[1] or times[1].date() > closed_at:
        raise ValueError("Fixture retest observations must be ordered between discovery and closure")
    if finding["closure_reference"] != observations[1]["id"]:
        raise ValueError("Closure must reference the passing fixture retest")
    evidence.update((item["id"], item) for item in observations)
    return {"before": observations[0]["id"], "after": observations[1]["id"]}


def analyze(fixture, as_of, root=ROOT):
    """Evaluate fixture facts, source presence and educational SLAs."""
    if fixture.get("schema_version") != 1 or fixture.get("synthetic") is not True:
        raise ValueError("Explicit versioned synthetic fixture required")
    if fixture.get("cloud_provider") != "AWS":
        raise ValueError("AWS-only scope: Azure deferred")
    period = fixture.get("period")
    if not isinstance(period, str) or len(period) != 7 or period != as_of.strftime("%Y-%m"):
        raise ValueError("Report period must match as-of month")
    if fixture.get("sla_days") != DEMO_SLA_DAYS:
        raise ValueError("Unreviewed remediation policy")
    if fixture.get("scan_freshness_days") != 30:
        raise ValueError("Demo scan freshness parameter must be explicit")
    boundary = fixture.get("boundary")
    if not isinstance(boundary, dict) or boundary.get("environment") != "synthetic":
        raise ValueError("Synthetic boundary required")

    aws = summarize_observations(fixture)
    mapping = fixture["control_mappings"]
    ids = [r["id"] for r in mapping]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Duplicate or empty control IDs")
    for row in mapping:
        if not row.get("limitation") or not row.get("evidence") or not row.get("owner"):
            raise ValueError("Control mapping must preserve gaps and ownership")
        if not row.get("title") or not set(row["observations"]).issubset(OBSERVATION_NAMES):
            raise ValueError("Invalid control description or AWS observation references")
        if row.get("status") != "partial_lab_mapping":
            raise ValueError("No control may be labeled compliant")

    source = source_inventory(root, mapping)
    controls = [{
        "control": row["id"], "title": row["title"], "owner": row["owner"],
        "scope": "selected_only_not_full_baseline",
        "status": "source_available_unassessed"
        if all(source[e]["status"] == "source_present" for e in row["evidence"])
        else "missing_source_evidence",
        "references": row["evidence"],
        "synthetic_aws_observations": {
            name: aws["observations"][name] for name in row["observations"]
        },
        "gap": row["limitation"]
    } for row in mapping]

    assets = fixture["assets"]
    asset_ids = [a["id"] for a in assets]
    if not assets or len(asset_ids) != len(set(asset_ids)):
        raise ValueError("Duplicate or empty asset IDs")
    coverage = Counter()
    for asset in assets:
        if asset.get("provider") != "AWS" or not asset.get("owner"):
            raise ValueError("Non-AWS or ownerless asset")
        scanned = asset.get("last_observed")
        if scanned is None:
            coverage["not_observed"] += 1
        else:
            observed = checked_date(scanned)
            days = (as_of - observed).days
            if days < 0:
                raise ValueError("Future observation is not accepted")
            coverage["current_fixture_observation" if days <= fixture["scan_freshness_days"]
                     else "stale_fixture_observation"] += 1

    findings = fixture["findings"]
    finding_ids = [f["id"] for f in findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise ValueError("Duplicate finding ID")
    rows = []
    retest_evidence = {}
    stats = Counter()
    period_start = as_of.replace(day=1)
    for f in findings:
        if f.get("asset_id") not in asset_ids:
            raise ValueError("Unknown affected asset")
        if not all(isinstance(f.get(k), str) and f[k].strip()
                   for k in ("id", "owner", "summary", "source", "control", "remediation")):
            raise ValueError("Incomplete finding")
        if f["control"] not in ids:
            raise ValueError("Unmapped finding")
        severity, state = f.get("severity"), f.get("status")
        if severity not in SEVERITIES or state not in STATUSES:
            raise ValueError("Invalid finding severity/status")
        discovered = checked_date(f["discovered"])
        if discovered > as_of:
            raise ValueError("Future finding")
        due = discovered + timedelta(days=DEMO_SLA_DAYS[severity])
        closed = f.get("closed_at")
        if state == "closed":
            if not closed or not f.get("closure_reference"):
                raise ValueError("Closure date and explicit fixture reference required")
            closed_at = checked_date(closed)
            if not discovered <= closed_at <= as_of:
                raise ValueError("Invalid closure date")
        elif closed is not None or f.get("closure_reference") is not None:
            raise ValueError("Open finding cannot claim closure")
        else:
            closed_at = None
        retest_links = None
        if (state == "closed" and f["control"] == "SI-2") or "retest" in f:
            retest_links = remediation_retest(f, discovered, closed_at, retest_evidence)
        overdue = state != "closed" and as_of > due
        resolution_late = bool(closed_at and closed_at > due)
        stats["new_this_month"] += discovered >= period_start
        stats["closed_this_month"] += closed_at is not None and closed_at >= period_start
        stats[state] += 1
        stats[severity] += 1
        if overdue:
            stats["overdue"] += 1
        if resolution_late:
            stats["late_closure"] += 1
        rows.append({
            "id": f["id"], "asset_id": f["asset_id"], "control": f["control"],
            "owner": f["owner"], "source": f["source"], "summary": f["summary"],
            "severity": severity, "status": state, "discovered": discovered.isoformat(),
            "due": due.isoformat(), "age_days": (as_of - discovered).days,
            "overdue": overdue,
            "overdue_days": max(0, (as_of - due).days) if overdue else 0,
            "days_to_close": (closed_at - discovered).days if closed_at else None,
            "closed_at": closed_at.isoformat() if closed_at else None,
            "late_closure": resolution_late,
            "remediation": f["remediation"],
            "closure_reference": f.get("closure_reference"),
            **({"retest_evidence_ids": retest_links} if retest_links else {}),
            "evidence_status": "synthetic_fixture_not_independently_verified",
            "no_official_fedramp_deadline_claim": True,
        })
    rows.sort(key=lambda f: (f["status"] == "closed", SEVERITIES.index(f["severity"]), f["id"]))

    metrics = {
        "findings_total": len(rows), "open": stats["open"] + stats["in_progress"],
        "closed_fixture": stats["closed"], "overdue_open": stats["overdue"],
        "late_closure": stats["late_closure"],
        "new_this_month": stats["new_this_month"],
        "closed_this_month": stats["closed_this_month"],
        "by_severity": {s: stats[s] for s in SEVERITIES},
        "assets_total": len(assets),
        "assets_with_current_fixture_observation": coverage["current_fixture_observation"],
        "assets_with_stale_fixture_observation": coverage["stale_fixture_observation"],
        "assets_without_fixture_observation": coverage["not_observed"],
        "control_mappings_with_all_sources": sum(x["status"] == "source_available_unassessed" for x in controls),
        "control_mappings_total": len(controls),
    }
    report = {
        "schema_version": 1, "synthetic": True, "provider": "AWS",
        "title": "Synthetic AWS FedRAMP-inspired monthly continuous monitoring",
        "period": period, "as_of": as_of.isoformat(),
        "statement": DISCLAIMER, "authorization": "none",
        "boundary": boundary,
        "remediation_policy": {"days_by_severity": DEMO_SLA_DAYS,
            "source": "educational_fixture_only_not_a_fedramp_requirement"},
        "scan_policy": {"freshness_days": 30, "source": "educational_fixture_only"},
        "metrics": metrics,
        "monitoring": {"synthetic_aws_observations": aws,
                       "service_level_monitoring": "not_implemented",
                       "finding_sources": "synthetic fixtures; no scanner execution",
                       "trends": "not_established_one_month_only"},
        "review": {
            "recommendation": "HUMAN_REVIEW_REQUIRED_NOT_AUTHORIZATION",
            "reason": "Review synthetic evidence coverage and open mock remediation items",
            "approver": None,
            "actual_ao_decision": None,
        },
        "references": {
            "nist_800_53_rev5": "https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
            "fedramp_2026": "https://www.fedramp.gov/2026/reference/rev5/b/vulnerability-detection-and-response/",
        },
    }
    poam = {
        "schema_version": 1, "synthetic": True, "scope": "fixture_only_not_official_poam",
        "statement": DISCLAIMER, "period": period,
        "as_of": as_of.isoformat(), "items": rows, "approval_status": "not_reviewed",
    }
    return report, poam, {
        "synthetic": True, "standard": "NIST SP 800-53 Rev. 5",
        "statement": DISCLAIMER, "status": "partial_mappings_only", "controls": controls,
    }, {"synthetic": True, "statement": DISCLAIMER, "files": source,
        "remediation_retests": retest_evidence}


def system_security_plan(fixture, report, mapping):
    return {
        "schema_version": 1,
        "synthetic": True,
        "title": "Synthetic AWS System Security Plan",
        "statement": DISCLAIMER,
        "period": report["period"],
        "as_of": report["as_of"],
        "boundary": report["boundary"],
        "aws_region": fixture["aws_region"],
        "assets": fixture["assets"],
        "control_mappings": "control-mappings.json",
        "mapped_controls": [control["control"] for control in mapping["controls"]],
        "monitoring_report": "monthly-report.json",
        "remediation_register": "poam.json",
        "data_flow": "Local synthetic fixture to offline analysis to local evidence bundle",
        "responsibility": "Synthetic asset and control owners review results and track mock remediation",
        "unresolved": ["System categorization and baseline selection", "Deployed identity, storage and logging verification",
                       "Operational monitoring coverage and independent review"],
    }


def dashboard(report, poam):
    """Static, escaped, dependency-free dashboard; no secret or account detail."""
    m = report["metrics"]
    cards = [
        ("New this month", m["new_this_month"]),
        ("Closed this month", m["closed_this_month"]),
        ("Open or in progress", m["open"]),
        ("Overdue mock findings", m["overdue_open"]),
        ("Late mock closures", m["late_closure"]),
        ("Current fixture observations", f'{m["assets_with_current_fixture_observation"]}/{m["assets_total"]}'),
    ]
    card_html = "".join(
        f'<div class="card"><strong>{html.escape(str(value))}</strong>'
        f'<span>{html.escape(label)}</span></div>' for label, value in cards)
    coverage = (
        f'{m["assets_with_stale_fixture_observation"]} stale and '
        f'{m["assets_without_fixture_observation"]} missing asset observations. '
        f'{m["control_mappings_with_all_sources"]}/{m["control_mappings_total"]} '
        'selected control mappings have their referenced source files.'
    )
    row_html = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(item.get(key) if item.get(key) is not None else '—'))}</td>"
                          for key in ("id", "severity", "status", "owner", "due", "overdue")) + "</tr>"
        for item in poam["items"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Synthetic AWS ConMon executive dashboard</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.45;color:#202a36}}
.banner{{background:#fff2d6;padding:1rem;border-left:5px solid #a45e00}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin:1.5rem 0}}
.card{{padding:1.25rem;background:#edf3f8;border-radius:8px}}
.card strong{{font-size:2rem;display:block}}.card span{{font-size:.9rem}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:.7rem;text-align:left;border-bottom:1px solid #ccc}}
th{{background:#e8edf1}}.scroll{{overflow-x:auto}}
</style></head><body><h1>Synthetic AWS ConMon executive dashboard</h1>
<p class="banner"><strong>NOT AUTHORIZED / SYNTHETIC:</strong> {html.escape(DISCLAIMER)}</p>
<p>Reporting month: {html.escape(report["period"])} · As-of: {html.escape(report["as_of"])} · Cloud: AWS only.</p>
<section class="cards" aria-label="Summary metrics">{card_html}</section>
<p>{html.escape(coverage)}</p>
<h2>Illustrative remediation register</h2><div class="scroll"><table><thead><tr>
<th>ID</th><th>Severity</th><th>Status</th><th>Owner</th><th>Demo due date</th><th>Overdue</th>
</tr></thead><tbody>{row_html}</tbody></table></div>
<p>Fixed example severity windows are NOT FedRAMP deadlines. Observations are simulated and may be stale or absent.
This dashboard does not establish control effectiveness or scan completeness.</p>
<p><strong>Human review required.</strong> No authorizing official decision, assessment, or live collection is represented.</p>
</body></html>
"""


def build(destination, as_of, fixture_path=FIXTURE, root=ROOT):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Choose a new output directory; overwrite is disabled")
    fixture_path = Path(fixture_path)
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    report, poam, mapping, evidence = analyze(fixture, checked_date(as_of), root)
    evidence["fixture_sha256"] = hashlib.sha256(fixture_bytes).hexdigest()
    evidence["aws_observation_summary"] = report["monitoring"]["synthetic_aws_observations"]
    outputs = {
        "monthly-report.json": canonical(report), "poam.json": canonical(poam),
        "control-mappings.json": canonical(mapping),
        "evidence-index.json": canonical(evidence),
        "ssp.json": canonical(system_security_plan(fixture, report, mapping)),
        "dashboard.html": dashboard(report, poam),
    }
    payloads = {name: data.encode("utf-8") for name, data in outputs.items()}
    manifest = {
        "schema_version": 1, "synthetic": True,
        "assertion": DISCLAIMER,
        "files": {name: hashlib.sha256(payload).hexdigest() for name, payload in payloads.items()},
    }
    # Exclusive directory creation prevents concurrent builds from overwriting each other.
    # The manifest is written last so an interrupted build cannot verify.
    destination.mkdir(parents=True)
    for name, payload in payloads.items():
        (destination / name).write_bytes(payload)
    (destination / "manifest.json").write_bytes(canonical(manifest).encode("utf-8"))
    verify(destination)
    return manifest


def verify(destination):
    destination = Path(destination).resolve()
    manifest = destination / "manifest.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("Missing or symlink manifest")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("synthetic") is not True:
        raise ValueError("Unexpected evidence manifest")
    if set(data.get("files", {})) != set(OUTPUTS):
        raise ValueError("Unexpected manifest contents")
    all_files = set()
    for item in destination.rglob("*"):
        if item.is_symlink():
            raise ValueError("Symlink in evidence")
        if item.is_file():
            all_files.add(item.relative_to(destination).as_posix())
    if all_files != set(OUTPUTS) | {"manifest.json"}:
        raise ValueError("Unexpected, added or missing file in evidence bundle")
    for name, recorded in data["files"].items():
        if not isinstance(recorded, str) or digest(destination / name) != recorded:
            raise ValueError("Evidence digest mismatch: " + name)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--output", help="New directory for safe synthetic artifacts")
    choice.add_argument("--verify", help="Verify existing artifact bundle hashes")
    parser.add_argument("--as-of", default="2026-11-20",
                        help="ISO date for deterministic simulation")
    parser.add_argument("--fixture", default=str(FIXTURE))
    args = parser.parse_args()
    if args.verify:
        verify(args.verify)
    else:
        build(args.output, args.as_of, args.fixture)
    print("PASS: synthetic AWS-only evidence hashes; NOT an assessment or authorization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
