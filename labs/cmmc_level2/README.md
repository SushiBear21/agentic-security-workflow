# Synthetic CMMC Level 2 readiness and assessment exercise

**TRAINING LAB ONLY — NOT CERTIFICATION, NOT A REAL ASSESSMENT, NO REAL CUI.**

Run from repository root: `python -m labs.cmmc_level2.assessment`; test with `python -m unittest discover -s tests -p 'test_cmmc_level2.py'`.

The generator validates the 110-requirement catalog and produces a fictional CUI asset inventory, 110-row evidence tracker, 110 interview prompts, synthetic SSP, open POA&M list and management no-go report under `labs/cmmc_level2/generated/`. Generated outputs are intentionally not committed; rerun to reproduce. Only explicitly simulated observations are marked; all other requirements are NOT_EVALUATED. Nothing is suitable for SPRS/eMASS or an actual assessor.

As of Nov 2026, official DoD CMMC guidance notes the July 2026 pause of Phase II and continuation of Phase I self-assessments. Level 2 baseline remains NIST SP 800-171 Rev 2 under 32 CFR Part 170, despite NIST's later Rev 3 publication. See [DoD CMMC](https://dodcio.defense.gov/CMMC/About/), [assessment guide](https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf), [32 CFR Part 170](https://www.ecfr.gov/current/title-32/part-170), [NIST Rev 2](https://doi.org/10.6028/NIST.SP.800-171r2), and [800-171A](https://doi.org/10.6028/NIST.SP.800-171A).

Assessment rules: 110 controls/14 families; objective-level examine/interview/test; limited POA&M eligibility and 180-day closeout; C3PAO versus self-assessment distinctions; weighted scoring must not be inferred from missing evidence. Existing portfolio controls can inspire demonstrations but do not prove CMMC implementation.

**Review gate:** validate exact regulatory version and all scoring/POA&M exclusions before using beyond training; independently review source catalog and objective transcription. No real AWS testing or production deployment was performed.
