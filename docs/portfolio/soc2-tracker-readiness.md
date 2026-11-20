# SOC 2 readiness exercise for the evidence tracker

This is a Security-category readiness exercise for a synthetic, local and CI
portfolio service. Its observed evidence comes from software tests and a GitHub
release rehearsals. The evidence supports the selected checks below. An
independent reviewer has yet to evaluate the workpapers, and there is no SOC 2
attestation or conclusion about period-wide operating effectiveness.

## System and evidence period

The boundary follows the [tracker design](evidence-tracker-release.md) and its
[system boundary diagram](cmmc-tracker-assessment.md#ssp-extract-and-boundary).
It covers contributor and reviewer access, workspace SQLite records, audit
export, the tracker repository branch, and the GitHub CI workflow that builds and
exercises the image. It excludes production hosting and customer data. The
control owner names below are proposed functional roles for the exercise.

**Observation window** November 18, 2026, 12:00 a.m. ET through November 20,
2026, 11:23 a.m. ET (November 18 05:00 to November 20 16:23 UTC, end exclusive).
The [population snapshot](audit-evidence/tracker-audit-population.json) records
the dates, sources, and upper bound used for the sample.

| Population | Source inspected | Items observed | Sample |
| --- | --- | ---: | --- |
| Tracker CI release rehearsals | [Tracker workflow history](https://github.com/SushiBear21/agentic-security-workflow/actions/workflows/evidence-tracker.yml) | 3 completed distinct runs | 3 of 3 technical rehearsals |
| Tagged releases and deployments | GitHub [releases](https://github.com/SushiBear21/agentic-security-workflow/releases), [tags](https://github.com/SushiBear21/agentic-security-workflow/tags), and [deployments](https://api.github.com/repos/SushiBear21/agentic-security-workflow/deployments) | 0 | None available |
| Submitted formal reviews on the sampled changes | GitHub [PR #13 reviews](https://api.github.com/repos/SushiBear21/agentic-security-workflow/pulls/13/reviews) and [PR #14 reviews](https://api.github.com/repos/SushiBear21/agentic-security-workflow/pulls/14/reviews) | 0 | None available |

Each run exercises a baseline, a deliberately blocked candidate, and a
recovery. These phases count as one rehearsal per workflow run. Two runs come
from the audit PR and repeat the tracker workflow. Each receipt records
`promotion_authorized: false`. The population supports technical checks
within this repository and observation window.

## Control workpapers

| ID and criterion | Designed control and owner | Procedure and observed evidence | Result and exceptions |
| --- | --- | --- | --- |
| S2-01 · CC6.1 and CC6.3 | The access owner provisions separate contributor and reviewer roles by workspace. The service restricts contributor reads and reviewer actions. | Inspect `tracker/store.py` and `tests/test_tracker.py`. Reperform the role and isolation tests. The [archived samples](tracker-audit-review-packet.md#sample-trace) report authentication, role isolation, digest-bound review, and audit export. | **Passed for the tested paths.** E-01 remains open for access lifecycle evidence. |
| S2-02 · CC8.1 | The release coordinator ties the change to scoped issues, verifies required gates, and obtains separate human authorization before promotion. | Match [PR #13](https://github.com/SushiBear21/agentic-security-workflow/pull/13) and issues [#8](https://github.com/SushiBear21/agentic-security-workflow/issues/8), [#9](https://github.com/SushiBear21/agentic-security-workflow/issues/9), and [#11](https://github.com/SushiBear21/agentic-security-workflow/issues/11) to the receipt. Verify the checkout SHA, scan image, SBOM, and technical decisions. Search for recorded PR approval and a promoted release. | **Technical gates passed in all three rehearsals.** Candidate blocked, recovery eligible for review, promotion unauthorized. E-02 remains open for approval and release history. |
| S2-03 · CC7.2 | The service operator monitors tracker health and investigates failed release checks. | Reperform the scan and receipt checks using the historical artifact. Compare the failed candidate smoke receipt with the successful recovery receipt, including preservation of the approved baseline record as reported by CI. | **CI failure detection and recovery verified.** E-03 remains open for ongoing monitoring and response evidence. |

## Exception register

| ID | Exception | Owner and closure evidence |
| --- | --- | --- |
| E-01 | Demo tokens and lab identities support role tests. Provisioning approvals, revocation and periodic access reviews were not observed. | Access owner. Retain an approved access request, a revoked identity test, and a dated access review. |
| E-02 | Three pre-merge rehearsals and zero observed promotions or formal reviews. | Release coordinator. Retain an independently approved change and a promotion or tagged-release receipt, then extend the sample when more releases exist. |
| E-03 | CI detects startup and workflow failures. There is no observed continuous telemetry, alert delivery or incident acknowledgement history. | Service operator. Exercise an alert and preserve a timestamped route, acknowledgement and resolution record. |

## Evidence and reproduction

The [reviewer packet](tracker-audit-review-packet.md) traces evidence requests
to the three samples, exceptions, and follow-up decisions. Generate the full
machine-readable packet by running:

```sh
python -m tracker.audit_workpapers --output tracker-audit-packet.json
```

To reperform the original baseline separately, use the commands below.


Use the [byte-identical retained ZIP](audit-evidence/tracker-ci-original.zip).
Its [GitHub Actions source artifact](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44249673451/artifacts/14403252146)
is scheduled to expire on December 18, 2026. Keep the retained ZIP intact and
compare it against the captured artifact digest before reperformance.

```sh
python -m unittest discover -s tests -p test_tracker.py -v
python -m tracker.audit_bundle --artifact docs/portfolio/audit-evidence/tracker-ci-original.zip --source docs/portfolio/audit-evidence/tracker-ci-source.json --output audit-observation.json
```

Compare the output with the [recorded observation](audit-evidence/tracker-ci-observation.json).
The verifier checks the original ZIP against the artifact hash captured from
GitHub and reruns the technical release decision using the historical scan
timestamp. This establishes what was observed in the rehearsal and does not
serve as a current vulnerability assessment.

[Source: AICPA Trust Services Criteria](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022)
