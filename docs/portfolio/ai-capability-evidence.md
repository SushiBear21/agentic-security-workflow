# AI operations and assurance evidence

Run the existing release entry point with Python 3.13 and the pinned requirements.

```sh
python -m pip install -r requirements.txt
python -m tower.release --output release-evidence
python -m tower.governance release-evidence
```

Use a new output directory for each rehearsal. CI installs `pip-audit` and passes
`--audit` to the release command. The dependency gate requires a successful
scan with a clean report covering every pinned application dependency. The scan
report and its hash are retained with the assessment. Running without `--audit`
supports network-isolated rehearsal and leaves that gate unmeasured.

The [prior human evaluation](../p4-final-results.md) failed all six injected
context drafts. The revised prompt sends only document IDs and verified
structured facts. The application supplies and validates an exact summary
that includes applicability uncertainty. The mock suite exercises rejection of
an unsupported compromise assertion and checks that retrieved prose stays
outside the provider payload. Human draft quality remains blocked pending a
fresh live comparison and human review. Run the existing evaluation and
interactive review described in the [demo guide](../p4-demo-guide.md), then pass
`--comparison path/to/comparison.json` to the release command. It validates the
matching `human-review.json`, verifies the comparison against the current
source, and records the eligibility result without packaging the raw drafts.

| Existing extension | Evidence |
| --- | --- |
| Deployment engineering | `canary.json` records model profile IDs, prompt version and hash, and per-request latency, tokens and estimated scenario cost. Candidate requests 0 and 10 include one safe response and one rejected response. The simulated router returns the final 19 requests to stable after the rejection. Stable accepted all 28 requests routed to it. The existing SQLite snapshot restoration is independently checked. |
| Federal AI compliance exercise | `governance.json` records fixture model and dataset inventories, synthetic risk owners, release status, exceptions and evidence hashes. The monitoring command checks a retained evidence directory for missing, expired (48 hours), modified or failing evidence. The daily GitHub job refreshes lab evidence. AI RMF mapping covers GOVERN, MAP, MEASURE and MANAGE. See [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1) and the [Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1). |
| Security Program Control Tower | `adversarial.json` records ten mocked-boundary cases, including eight adversarial cases across five categories and two benign controls. The local rehearsal observed 0/8 adversarial boundary failures and 0/2 benign failures. The RAG repository separately exercises direct question injection with a simulated guardrail response. |
| Enterprise AI delivery | `adoption.json` combines the synthetic cohort, the existing workflow metrics, and a separately priced model-traffic scenario. |

The host creates one agent tool capability per run, with a 180-second monotonic-clock lifetime and a bounded call count. Scope covers listing synthetic candidates, reading listed candidates, and proposing a review for the required highest-ranked candidate after reading it. The model cannot set the principal or lifetime. The host records the capability principal and allowed/denied tool decisions on both successful and failed CLI attempts. The human approval and exact-payload verification paths remain independent. The capability is process-local and carries no AWS credentials. Local actors in the rehearsal are fixture identities.

## Synthetic delivery case study

Three fictional users were eligible. Two completed a workflow and one of two previously active users returned. Two of three attempts completed and one of two reviewed drafts was accepted. Two paired task times averaged 10 seconds saved, using fixture inputs. The SQLite rehearsal recorded one independent approval with five seconds of fixture-supplied effort and one correctly blocked unapproved attempt. The model workload scenario costs $0.006 for 30 mocked requests at assumed token rates. Fixture timings and token counts do not estimate production latency or provider billing.

These results describe repository fixtures and application controls. Live injection resistance, real end-user adoption, measured productivity, cloud release behavior, and compliance authorization remain unverified.
