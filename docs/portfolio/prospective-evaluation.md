# Prospective Bedrock holdout and lab release protocol

This protocol applies to the next evaluation. Commit it before collecting
outputs. Keep the holdout fixtures out of prompt tuning and report all failures.
The scope is synthetic inventory drafting and authorization-bound retrieval.

| Criterion | Threshold fixed before the run |
| --- | --- |
| Coverage | Two configurations, one repeat, three cases each, four live model calls |
| Contract | All six checks pass, including zero model calls for the restricted case |
| Independent review | All four held-out drafts pass. A second person judges each draft against the source and records a source ID and factual rationale |
| Latency and cost | Every live call at or below 15 seconds. Known total estimated cost at or below USD 1 |
| Container scan | Fresh Trivy report for the exact local image ID. OS and language package coverage with zero high or critical findings |
| Lab release approval | A named person distinct from the evaluation owner approves the exact evidence manifest hash |

Pass a draft when the source supports the exposure and business-criticality
claims, the cited source is correct, and the response preserves uncertainty
about applicability without inventing a vulnerability or claiming execution.
Reviewers should explain which source facts support the judgment or name the
specific discrepancy. Have the reviewer score before sharing owner judgments.

Run the holdout from the protocol revision with the existing sandbox profile.
Get the image ID and raw Trivy JSON from the trusted container CI artifact for
this revision. Use verified current token prices for the selected model.

```sh
python p4_observability.py --holdout --live --release-id IMAGE_ID --input-price INPUT --output-price OUTPUT --price-date YYYY-MM-DD
python -m tower.release_record packet --report comparison.json --owner "Evaluation owner" --output independent-review.json
```

Use the report path printed by the evaluator. The reviewer enters their name,
a pass or fail judgment, source ID, and factual rationale for each of the four
drafts in the packet. Preserve the original report and completed packet.

Use the raw Trivy JSON from the trusted container CI run and the image ID
recorded by that same run. The scan must be no more than 24 hours old at
finalization. If review takes longer, rescan the same image ID or start a new record for the new image.

```sh
python -m tower.release_record manifest --report comparison.json --owner "Evaluation owner" --review independent-review.json --scan container-vulnerabilities.json --image-id IMAGE_ID --output manifest.json
```

After inspecting the evidence and gates, an approver distinct from the owner
records their decision in a separate file:

```json
{"approver":"Approver name","decision":"approve","manifest_sha256":"SHA-256 printed by the manifest command"}
```

```sh
python -m tower.release_record finalize --report comparison.json --owner "Evaluation owner" --review independent-review.json --scan container-vulnerabilities.json --image-id IMAGE_ID --manifest manifest.json --approval approval.json --output release-record.json
```

A lab release requires every gate and approval to pass. The record binds the
report, protocol, reviewer packet, scan and approval by hash. Keep those
inputs with the record. Reviewer and approver identities are self-attested,
and the record grants no AWS deployment authority.
