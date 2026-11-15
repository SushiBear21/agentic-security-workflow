import hashlib
import html
import json
import zipfile
from collections import Counter
from pathlib import Path
from tower.core import metrics, verify, CONTROLS


def export(state, directory):
    verify(state)
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    m = metrics(state)
    esc = lambda value: html.escape(str(value))
    rows = []
    for f in state["findings"].values():
        tickets = [t for t in state["tickets"].values() if t["payload"]["finding_id"] == f["id"]]
        status = ", ".join(t["status"] for t in tickets) or "AWAITING REVIEW"
        rows.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in [f["id"], f["title"], f["kind"], f["owner"], f["likelihood"]*f["impact"], ", ".join(CONTROLS[f["category"]][0]), f["milestone"], f["due"], ", ".join(f["dependencies"]) or "None", status]) + "</tr>")
    states = Counter(p["state"] for p in state["proposals"].values())
    cards = [("Findings", len(rows)), ("Pending decisions", states["PENDING"]), ("Approved", states["APPROVED"]), ("Synthetic tickets", len(state["tickets"]))]
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Security Program Control Tower</title>
<style>body{margin:0;background:#0c1424;color:#e8eef7;font:16px system-ui}main{max-width:1450px;margin:auto;padding:40px 24px}h1{font-size:36px;letter-spacing:-1px}h2{margin-top:36px}.eyebrow{color:#6ee7cf;letter-spacing:2px}.notice{padding:18px;border:1px solid #ba9853;background:#2a251e;border-radius:10px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:24px 0}.card{background:#18253a;padding:24px;border-radius:12px}.number{font-size:38px;display:block;color:#6ee7cf}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:14px;text-align:left;border-bottom:1px solid #334155}th{color:#8eaccb}details{background:#18253a;padding:20px;border-radius:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#6ee7cf}.muted{color:#a6b7cb}</style><main><div class="eyebrow">SECURITY GOVERNANCE / PORTFOLIO LAB</div><h1>AI Security Program Control Tower</h1><p class="muted">Synthetic findings → mapped requirements → human decisions → tracked remediation</p>
<div class="notice">Synthetic demonstration. AI quality gate remains <strong>BLOCKED</strong>. Tickets do not change AWS resources. Control mappings are illustrative, not compliance evidence.</div><section class="cards">"""
    page += "".join(f'<div class="card">{esc(label)}<strong class="number">{value}</strong></div>' for label, value in cards)
    page += "</section><h2>Program register</h2><p class='muted'>Risk = likelihood × impact (1–25). Closure requires resolved dependencies and recorded evidence.</p><div class='scroll'><table><thead><tr>" + "".join(f"<th>{h}</th>" for h in ["ID", "Finding", "Source", "Owner", "Risk", "NIST", "Milestone", "Due", "Depends on", "Status"]) + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    page += "<h2>Measured outcomes</h2><p class='muted'>Null means unmeasured. Review elapsed time includes queue time; effort is self-reported. Reliability includes denied workflow commands; it is not availability.</p><details open><summary>Metric values and denominators</summary><pre>" + esc(json.dumps(m, indent=2)) + "</pre></details>"
    page += "<h2>Evidence & decisions</h2><p><a href='evidence.zip'>Download evidence package</a> · <a href='manifest.json'>SHA-256 manifest</a></p><p class='muted'>Hash chaining detects accidental edits; a privileged operator can rewrite the store and chain. No independent approval or immutable audit guarantee.</p><details><summary>Approval queue — exact payloads</summary><pre>" + esc(json.dumps(state["proposals"], indent=2)) + "</pre></details></main></html>"
    files = {"dashboard.html": page, "state.json": json.dumps(state, indent=2, allow_nan=False), "metrics.json": json.dumps(m, indent=2),
             "controls.json": json.dumps(CONTROLS, indent=2)}
    manifest = {name: hashlib.sha256(body.encode()).hexdigest() for name, body in files.items()}
    files["manifest.json"] = json.dumps(manifest, indent=2)
    for name, body in files.items():
        (destination / name).write_text(body, encoding="utf-8")
    with zipfile.ZipFile(destination / "evidence.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body.encode())
    return destination / "dashboard.html"


def verify_package(path):
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if set(archive.namelist()) != set(manifest) | {"manifest.json"}:
            raise ValueError("Unexpected package entries")
        for name, expected in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Package digest mismatch: " + name)
        verify(json.loads(archive.read("state.json")))
    return True
