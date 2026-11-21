# Ten-minute portfolio walkthrough

Start at the [portfolio overview](../../PORTFOLIO.md). This route works as a
self-guided review or an interview demonstration; no AWS deployment is needed.

| Time | Project | Evidence to open and what it shows |
| --- | --- | --- |
| 0–2 min | [Secure Enterprise RAG](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/README.md#objective-success-criteria-and-evidence) | [Employee results](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/tests/evaluation/live-employee-results.json) and [SOC results](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/tests/evaluation/live-soc-results.json) show 6/6 and 3/3 recorded sandbox cases passing. Use the [retrieval boundary tests](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/tests/security/test_retrieval_boundary.py) to show how unauthorized evidence is kept out of model context. |
| 2–4 min | [AI Cyber Threat Intelligence](https://github.com/SushiBear21/ai-cyber-threat-intel/blob/main/README.md#objective-success-criteria-and-evidence) | The [reviewed synthetic report](https://github.com/SushiBear21/ai-cyber-threat-intel/blob/main/docs/samples/reviewed-report.md) shows how source evidence and scoring support an analyst priority. The [AWS run record](https://github.com/SushiBear21/ai-cyber-threat-intel/blob/main/docs/automation-verification.md) records three candidates, repeat-input skipping, and a failure alert. |
| 4–6 min | [AWS Security Response Lab](https://github.com/SushiBear21/aws-security-response-lab/blob/main/README.md#objective-success-criteria-and-evidence) | The [response and rollback record](https://github.com/SushiBear21/aws-security-response-lab/blob/main/docs/response-results.md) shows denied approvals, repeat execution behavior, and restoration of the baseline security group on an unattached lab interface. |
| 6–8 min | [Agentic Security Workflow](https://github.com/SushiBear21/agentic-security-workflow/blob/main/README.md#objective-success-criteria-and-evidence) | The [approval run](../approval-verification.md) shows denial before approval and ticket reuse after approval. Compare the [original blocked quality decision](../p4-final-results.md) with the [separate approved Bedrock holdout](customer-deployment.md#approved-bedrock-holdout-lab-release), which cleared all five gates for a lab release. |
| 8–10 min | [Loyalty Fraud Detection Lab](https://github.com/SushiBear21/loyalty-fraud-detection-lab/blob/main/README.md#objective-success-criteria-and-evidence) | Compare the [lab targets](https://github.com/SushiBear21/loyalty-fraud-detection-lab/blob/main/docs/PROJECT_PLAN.md#objectives-and-success-measures) with the [synthetic dashboard](https://github.com/SushiBear21/loyalty-fraud-detection-lab/blob/main/reports/dashboard.md): all attempted fraud miles held or reviewed, 3.3% legitimate-member friction, and 81.3% queue precision. Open the [sample review queue](https://github.com/SushiBear21/loyalty-fraud-detection-lab/blob/main/reports/review_queue_sample.csv) to see the reasons an analyst receives. |

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
