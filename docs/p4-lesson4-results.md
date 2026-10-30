# Project 4 — Lesson 4: Context Management

## Scope

A context gate checks supplied synthetic evidence before passing
approved documents to the bounded reliability workflow.

## Observed validation

- Ten context scenarios passed.
- Nine context unit tests passed.
- All 30 unit tests across lessons 1-4 passed.
- Missing, unrelated, and restricted evidence caused abstention.
- Conflicting structured facts caused abstention.
- Oversized context was rejected.
- Sensitive context was blocked without returning its contents.
- Malformed metadata and duplicate citation IDs were rejected.
- Injected document instructions did not change the permitted action.
- Existing tool authorization remained enforced.
- Sensitive and attack canaries were absent from the saved report.

## Limits

The context limit is 4,000 serialized characters, not model tokens.
Audience and sensitivity labels are trusted synthetic fixtures.
No real authentication or general sensitive-data detection is tested.
The deterministic reference uses structured facts and ignores document
instructions; this does not establish live model injection resistance.
No model calls or AWS calls occur.

## Next lesson

Add live model evaluation and measure quality, latency,
token usage, and estimated cost.
