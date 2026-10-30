import argparse
from datetime import datetime, timezone
import html
import json
import math
from pathlib import Path
import statistics

from p4_review import (
    digest, validate_report, verify_sources,
    validate_review, counts,
)

ROOT = Path(__file__).resolve().parent


def fallback_drill():
    from p4_baseline import dataset, draft_review, grade

    case = dataset()[0]

    rejected = grade(
        draft_review(case["input"], broken=True),
        case["expected"],
    )

    restored = grade(
        draft_review(case["input"]),
        case["expected"],
    )

    passed = (
        {"action", "applicability", "citations"}.issubset(rejected)
        and not restored
    )

    result = {
        "mode": "offline_fallback_drill",
        "passed": passed,
        "candidate_rejected": bool(rejected),
        "reference_fallback_passed": not restored,
        "production_changed": False,
        "time": datetime.now(timezone.utc).isoformat(),
    }

    folder = ROOT / "reports" / "p4-session8"
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "fallback-drill.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    if not passed:
        raise ValueError("Fallback drill failed")

    return result


def assess(report, review):
    live = [
        row for row in report["results"]
        if row["model_called"]
    ]

    known = all(
        type(row.get("estimated_cost_usd")) in (int, float)
        and math.isfinite(row["estimated_cost_usd"])
        and row["estimated_cost_usd"] >= 0
        for row in live
    )

    total = (
        sum(row["estimated_cost_usd"] for row in live)
        if known else None
    )

    budget = report.get("soft_budget_usd")

    cost_ok = (
        known
        and type(budget) in (int, float)
        and math.isfinite(budget)
        and 0 < budget <= 1
        and total <= budget
    )

    results = []

    for config in report["configurations"]:
        name = config["name"]

        rows = [
            row for row in report["results"]
            if row["config"] == name
        ]

        model = [
            row for row in rows
            if row["model_called"]
        ]

        human = [
            row for row in review["rows"]
            if row["config"] == name
        ]

        latencies = [
            row.get("model_latency_ms")
            for row in model
        ]

        valid_times = (
            len(latencies) == 12
            and all(
                type(value) in (int, float)
                and math.isfinite(value)
                and value >= 0
                for value in latencies
            )
        )

        reasons = []

        if (
            len(rows) != 36
            or not all(row["passed"] is True for row in rows)
        ):
            reasons.append("contract_checks")

        if (
            len(human) != 12
            or any(row["judgment"] != "pass" for row in human)
        ):
            reasons.append("human_review")

        if not valid_times or max(latencies) > 15000:
            reasons.append("latency_target")

        if not cost_ok:
            reasons.append("cost_accounting_or_target")

        results.append({
            "configuration": name,
            "eligible": not reasons,
            "reasons": reasons,
            "contract_passes": sum(row["passed"] for row in rows),
            "human_passes": sum(
                row["judgment"] == "pass" for row in human
            ),
            "model_calls": len(model),
            "median_ms": (
                round(statistics.median(latencies), 3)
                if valid_times else None
            ),
            "max_ms": (
                round(max(latencies), 3)
                if valid_times else None
            ),
            "estimated_usd": (
                sum(row["estimated_cost_usd"] for row in model)
                if known else None
            ),
        })

    eligible = [
        row for row in results
        if row["eligible"]
    ]

    chosen = (
        min(
            eligible,
            key=lambda row: (
                row["median_ms"],
                row["estimated_usd"],
            ),
        )["configuration"]
        if eligible else None
    )

    return results, chosen, total


def finish(path):
    report = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    live = validate_report(report)
    verify_sources(report)

    review_path = path.with_name("human-review.json")

    review = json.loads(
        review_path.read_text(encoding="utf-8-sig")
    )

    validate_review(
        review, digest(path), live
    )

    if counts(review)["pending"]:
        raise ValueError(
            "Session 7 has pending human judgments. "
            "Finish those first."
        )

    drill = fallback_drill()
    metrics, chosen, total = assess(report, review)

    decision = {
        "time": datetime.now(timezone.utc).isoformat(),
        "scope": "local laboratory recommendation; no deployment",
        "status": (
            "eligible_for_lab_demonstration"
            if chosen else "blocked"
        ),
        "recommended_configuration": chosen,
        "selection_rule": (
            "Eligible configurations: lowest observed "
            "median latency, cost as tie-breaker"
        ),
        "report_sha256": digest(path),
        "review_sha256": digest(review_path),
        "reviewer": review["reviewer"],
        "configurations": metrics,
        "known_total_estimated_usd": total,
        "criteria": (
            "36/36 contract checks; 12/12 human drafts; "
            "every model call <=15000 ms; known total run "
            "cost within its positive soft budget <=USD 1"
        ),
        "criteria_timing": (
            "Set in session 8 after measurement; retrospective "
            "lab check, not a prespecified benchmark"
        ),
        "fallback_drill": drill,
    }

    output = ROOT / "reports" / "p4-session8"
    output.mkdir(parents=True, exist_ok=True)

    (output / "readiness.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)

    table = [
        "| Configuration | Contract passes | Human passes | Median ms | Max ms | Estimated USD | Eligible |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in metrics:
        cost = (
            f"{row['estimated_usd']:.6f}"
            if row["estimated_usd"] is not None
            else "unknown"
        )

        table.append(
            f"| {row['configuration']} "
            f"| {row['contract_passes']}/36 "
            f"| {row['human_passes']}/12 "
            f"| {row['median_ms']} "
            f"| {row['max_ms']} "
            f"| {cost} "
            f"| {row['eligible']} |"
        )

    lines = [
        "# Project 4 - Final laboratory decision",
        "",
        "Status: " + decision["status"],
        "Recommended configuration: " + (
            chosen or "NONE - blocked"
        ),
        "",
    ] + table + [
        "",
        "## Decision basis",
        "",
        decision["criteria"],
        decision["criteria_timing"],
        decision["selection_rule"],
        "The choice is provisional: 12 model calls per configuration cannot establish statistical superiority.",
        "These targets are lab criteria, not a production availability or latency SLO.",
        "Cost estimates use recorded prices; the soft stop is not a guaranteed billing cap.",
        "",
        "## Evidence",
        "",
        "Report SHA-256: " + decision["report_sha256"],
        "Review SHA-256: " + decision["review_sha256"],
        "Fallback drill: broken candidate rejected; reference fallback passed; no production change.",
        "",
        "## Remaining boundaries",
        "",
        "Synthetic fixtures, a small development dataset, and a single human reviewer limit these results.",
        "Existing app.agent/app.workflow integration, model-driven planning, durable concurrent idempotency, and production deployment remain untested by this companion.",
        "See the governance matrix for the open risks. No NIST compliance or production-readiness certification is asserted.",
    ]

    (docs / "p4-final-results.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    esc = lambda value: html.escape(str(value))

    body = "".join(
        "<tr>"
        + "".join(
            "<td>" + esc(row[field]) + "</td>"
            for field in (
                "configuration",
                "contract_passes",
                "human_passes",
                "model_calls",
                "median_ms",
                "max_ms",
                "estimated_usd",
                "eligible",
            )
        )
        + "</tr>"
        for row in metrics
    )

    page = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>AI Evaluation Results</title>
<style>
body{font:16px system-ui;max-width:1100px;margin:40px auto;
padding:24px;background:#111b2b;color:#eef4ff}
h1{color:#77ddd0}
table{border-collapse:collapse;width:100%}
td,th{padding:10px;border:1px solid #52647e;text-align:left}
.scroll{overflow:auto}
p{line-height:1.6}
small{overflow-wrap:anywhere}
</style>
<h1>AI Evaluation and Reliability</h1>
"""

    page += (
        "<p>Status: <strong>"
        + esc(decision["status"])
        + "</strong><br>Recommendation: "
        + esc(chosen or "None")
        + "</p>"
    )

    page += (
        '<div class="scroll"><table><tr>'
        + "".join(
            "<th>" + heading + "</th>"
            for heading in (
                "Configuration",
                "Contract /36",
                "Human /12",
                "Model calls",
                "Median ms",
                "Max ms",
                "Estimated USD",
                "Eligible",
            )
        )
        + "</tr>" + body + "</table></div>"
    )

    page += (
        "<p>72 contract checks, including 48 policy-only checks "
        "and 24 model responses. Model latency excludes policy-only "
        "checks. Targets were set after measurement for a local "
        "demonstration. Small sample, estimated costs, single reviewer; "
        "no production certification.</p>"
        "<p>Fallback drill: broken candidate rejected; reference "
        "fallback passed. No production change.</p>"
        "<small>Report SHA-256: "
        + esc(digest(path))
        + "<br>Review SHA-256: "
        + esc(digest(review_path))
        + "</small></html>"
    )

    (docs / "p4-dashboard.html").write_text(
        page, encoding="utf-8"
    )

    (docs / "p4-operations-runbook.md").write_text(
        """# Project 4 - Operations runbook

## Lab targets and measurement

Use p4-final-results.md for the criteria and actual decision.
Criteria were set in session 8 after initial measurement.
They are retrospective lab checks, not production SLOs.
CI measures reference behavior; live runs measure the recorded
Bedrock drafting configurations.

## Failure handling

1. Stop further live runs and preserve the exact failed run folder.
2. Inspect error type, case/config/repeat, raw synthetic model output,
   and provider request ID where available.
3. Classify access/transport, schema, unsupported facts, injection,
   or token-accounting failure.
4. Correct the specific cause in a versioned change. Keep strict
   checks and the original failure evidence.
5. Run offline tests and CI first. A prompt/model/source change
   needs a new live evaluation and human review before a new recommendation.
6. Unknown accounting and failed human judgments block the affected
   recommendation. Do not change report hashes or judgments to make it pass.

## Recovery and fallback

Run python p4_finish.py --drill to reject the broken local candidate
and recheck the reference fallback.
This is a local test, not a deployed rollback.

A real code regression requires a reviewed revert of the specific
change and renewed validation. Avoid destructive reset or force pushes.

## Cost controls and reevaluation

Each full live run allows up to 24 attempted model calls and
512 output tokens per call, with no SDK retries.

The USD threshold is checked between calls and can overshoot by
one request. Timed-out provider calls may still incur charges.
Treat AWS billing as authoritative.

Reevaluate when prompt, model/configuration, evaluated source,
dataset, or intended use changes, or when a new failure is observed.

Production operation would require larger held-out datasets,
ongoing live monitoring, authenticated authorization,
independent review, and durable evidence.

## Retention

Keep raw reports/reviews and local settings out of Git and
back them up privately. CI artifacts expire after 14 days.

No persistent AWS infrastructure was created by this companion;
there is no Project 4 infrastructure teardown.
""",
        encoding="utf-8",
    )

    (docs / "p4-demo-guide.md").write_text(
        """# Project 4 - Five-minute demonstration

1. Explain the decision: which bounded drafting configuration
   meets the laboratory criteria?
2. Open p4-dashboard.html locally and compare actual contract checks,
   human judgments, latency, and estimated cost.
3. Explain that 72 checks include 24 model responses;
   the other checks stop before inference.
4. Show the initial schema failures and the documented
   explicit-schema prompt correction from lesson 5.
5. Show one injection case, one blocked sensitive case,
   and the source-linked human review results.
6. Open the governance matrix and distinguish implemented
   lab mechanisms from production recommendations.
7. Show p4-final-results.md and the local fallback drill.
   A blocked recommendation is a valid finding, not permission
   to hide a failure.

Use the README architecture diagram.

State that model planning is deterministic, tool faults are synthetic,
and this companion does not deploy or integrate the existing
approval workflow. Configuration selection is provisional because
the sample is small.

GitHub may show HTML source rather than render the dashboard.
Download it and open it locally.
The final-results Markdown provides the same core comparison on GitHub.
""",
        encoding="utf-8",
    )

    readme = ROOT / "README.md"

    text = (
        readme.read_text(encoding="utf-8-sig")
        if readme.exists()
        else "# Agentic Security Workflow\n"
    )

    marker = "## Project 4: AI evaluation and reliability"

    if marker not in text:
        text += """

## Project 4: AI evaluation and reliability

A bounded synthetic drafting companion with regression checks,
a measured two-configuration model comparison, human review,
governance evidence, and a documented local readiness decision.

```mermaid
flowchart TD
    A[Request and synthetic evidence] --> B[Context gate]
    B -->|Rejected| C[Abstain]
    B -->|Approved| D[Authorized bounded workflow]
    D --> E[Reference or Bedrock draft]
    E --> F[Output validation]
    F --> G[Human review and lab decision]
```

- [Measured model comparison](docs/p4-lesson5-results.md)
- [CI evidence](docs/p4-lesson6-results.md)
- [Human review](docs/p4-lesson7-results.md)
- [Governance matrix](docs/p4-governance-matrix.md)
- [Final decision and comparison](docs/p4-final-results.md)
- [Dashboard HTML - download and open locally](docs/p4-dashboard.html)
- [Operations runbook](docs/p4-operations-runbook.md)
- [Demonstration guide](docs/p4-demo-guide.md)

This is a laboratory evaluation companion.
Read the final decision and remaining risks before interpreting
its results as readiness for any broader use.
"""

        readme.write_text(text, encoding="utf-8")

    print("Decision:", decision["status"])
    print("Recommended configuration:", chosen or "NONE")
    print(
        "Generated final results, dashboard, runbook, "
        "demo guide, and README links."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report")
    parser.add_argument("--drill", action="store_true")
    args = parser.parse_args()

    if args.drill:
        print(json.dumps(fallback_drill(), indent=2))
    elif args.report:
        finish(Path(args.report))
    else:
        parser.error("Use --report PATH or --drill")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(
            "Finalization stopped: " + str(error)
        )