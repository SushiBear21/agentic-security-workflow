# Ten-minute portfolio walkthrough

Start at the [portfolio overview](../../PORTFOLIO.md). This route works as a
self-guided review or an interview demonstration; no AWS deployment is needed.

| Time | Show | Explain |
| --- | --- | --- |
| 0–2 min | [Four-project overview](../../PORTFOLIO.md) | How retrieval, analysis, response and program oversight fit together |
| 2–4 min | [Control Tower workflow](../control-tower.md) | The application owns authoritative fields; a human approves the exact proposal; execution is separate |
| 4–6 min | [AI evaluation decision](../p4-final-results.md) | Structural success did not satisfy human quality; explain the small dataset and reviewer limitations |
| 6–8 min | [Deployment pipeline](deployment-automation.md) and [CI](https://github.com/SushiBear21/agentic-security-workflow/actions) | Image scanning, SBOM, exact-plan approval, rollback and what has not run live |
| 8–10 min | [SSP](synthetic-ssp.md), [POA&M](poam.json), [adoption](adoption-measurement.md) | Evidence ownership, open risks, acceptance and operational handoff |

## Optional offline demonstration

From the agentic-security-workflow repository root with Python 3.13, use a new
database path to avoid changing an existing demonstration:

```powershell
python -m tower --db tower-data/presentation.sqlite ingest tower/fixtures.json
python -m tower --db tower-data/presentation.sqlite propose SEC-001
python -m tower --db tower-data/presentation.sqlite inspect
```

Show the proposal hash and reference-fixture label. This path has made no model
call and has not approved or executed anything. To demonstrate the human decision
and ticket lifecycle, follow the [existing quick start](../control-tower.md),
adding the same `--db tower-data/presentation.sqlite` before each subcommand.
Enter the actual review duration; do not present a demonstration value as measured savings.

Export a report from that same database:

```powershell
python -m tower --db tower-data/presentation.sqlite export tower-output/presentation
python -m tower verify tower-output/presentation/evidence.zip
```

Open the dashboard path printed by export. Explain that it is a generated report,
not a production operations console. Package verification checks integrity, not
independent authorship or approval authenticity.

## Questions to be ready for

- Why is authorization separate from model guardrails?
- What happens if approval expires or the payload changes?
- What does a passing CI result establish, and what does it leave untested?
- Why did the AI-quality decision remain blocked?
- Which metrics are measured, self-reported, synthetic, or missing?
- What would be required before a real customer deployment?

Use the linked implementation and results to answer. Keep lab outcomes separate
from professional deployment experience and independent compliance assurance.
