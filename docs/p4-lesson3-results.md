# Project 4 — Lesson 3: Tool Reliability

## Scope

Synthetic retrieval failures test bounded retries, failure
classification, response validation, and shared attempt limits.

A separate in-memory review-store fixture tests idempotency.

## Observed validation

- Eight reliability scenarios passed.
- Nine reliability unit tests passed.
- All 21 unit tests across lessons 1-3 passed.
- Temporary failures were retried within three total attempts.
- Permanent and malformed failures stopped after one attempt.
- Unauthorized plans dispatched zero retrieval attempts.
- Multiple workflow steps shared one attempt budget.
- Identical idempotency keys and payloads created one record.
- Changed payloads could not reuse an existing key.

## Limitations

Failures and retry delays are simulated.
No actual API timeout, network cancellation, or waiting is measured.
The review store is in memory and does not test durable,
concurrent, or crash-safe idempotency.
No model calls, AWS calls, or real ticket creation occur.

## Next lesson

Evaluate missing, conflicting, oversized, malicious,
restricted, and sensitive context.
