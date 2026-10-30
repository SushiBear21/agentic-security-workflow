# Project 4 - Operations runbook

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
