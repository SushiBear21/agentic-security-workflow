# Synthetic AWS continuous monitoring

This portfolio exercise simulates one month of AWS evidence review, vulnerability
remediation and executive reporting. All published observations, dates, owners and
findings are synthetic. The package conveys no authorization, assessment or control
effectiveness conclusion.

## Generate the monthly package

Run these commands from the repository root with Python 3.13. Choose a new output
directory for each run. The default fixture covers November 2026.

```sh
python -m tower.fedramp_conmon --as-of 2026-11-20 --output tower-output/conmon-aws
python -m tower.fedramp_conmon --verify tower-output/conmon-aws
```

Open `dashboard.html` locally. The same bundle contains:

| File | Contents |
| --- | --- |
| `monthly-report.json` | Month-to-date intake and closure, open backlog, mock observation freshness and review status |
| `poam.json` | Mock finding, owner, planned action, target, overdue days and closure reference |
| `ssp.json` | Fictional AWS boundary, asset inventory, responsibilities and outstanding work |
| `control-mappings.json` | Selected controls with source paths, simulated observations and gaps |
| `evidence-index.json` | Fixture SHA-256, reference file hashes, simulated AWS observation summary and synthetic remediation retest records |
| `manifest.json` | Output hashes for integrity verification |

For a different month, use `--fixture` with a version 1 synthetic AWS fixture
based on [the checked-in example](../../tests/fixtures/conmon-aws-v1.json).
Set its period and choose an as-of date in that month. Capture the register as
of that date and retain older open findings so they carry forward. The command
rejects observations, findings and closures dated after the reporting cutoff.
Counts for new findings and closures begin on day one. Backlog and late-closure
totals cover the full supplied register. The manifest detects mismatched files
against its recorded hashes. It is unsigned.

## Review the mock remediation register

The demo uses calendar-day targets of 2, 7, 30 and 90 days for critical, high,
moderate and low findings respectively. An unresolved item becomes overdue the
day after its target. A closure counts as late when its recorded closure date
falls after its target. Asset observations up to 30 days old are current in
the simulation, and stale and missing observations are counted separately.
These parameters are educational. Consult the published rules for applicable
requirements. [FedRAMP vulnerability detection and response](https://www.fedramp.gov/2026/reference/rev5/b/vulnerability-detection-and-response/)

The exercise maps AC-3, AU-2, CA-7, RA-5, SC-28 and SI-2. Read each mapping's
gap alongside its source and observation status. A file hash records the bytes
available at generation time, and a collected flag records a simulated
configuration response. [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)

## Reusable AWS collector

The separate [read-only collector](continuous-monitoring.md) supports an existing
AWS account, DynamoDB table and S3 bucket. It checks the caller account, exact
table ARN and bucket region, and sends the expected bucket owner on every S3
call. The collector reads configuration metadata. Keep live snapshots private.
The reporting command has no live collection or live snapshot input.

## Verification

The repository test workflow runs the unit suite, generates the fixed November
bundle, verifies its manifest and uploads the synthetic files. AWS collector
tests use stubbed responses and exercise account, resource and region scope as
well as a configuration read denied by S3.

On November 20, 2026, all 108 local unit tests passed on Python 3.13.15. The local run also generated and verified the bundle. The
example reports five findings, three open or in progress, one overdue, one late
closure, and one current observation out of three assets. Review the stale and
missing assets and the unverified logging observation alongside those counts.

## Parking lot

Azure remains deferred.

### Review the SYN-003 remediation retest

In `poam.json`, follow SYN-003's `retest_evidence_ids` into
`evidence-index.json` → `remediation_retests`. `SYN-003-BEFORE` shows that the
mock remediation confirmation was missing, so the check failed.
`SYN-003-RETEST` repeats the same check on the same synthetic asset/control
with the confirmation present, so it passes. The POA&M's closure reference
points to this passing record. Each record has its own UTC timestamp and
SHA-256 of the canonical record without the hash field.

This is a fixture-only SI-2 example; no AWS resource was patched or
retested, and it does not establish operational effectiveness or independent
closure. SYN-004 remains a date-only exercise.
