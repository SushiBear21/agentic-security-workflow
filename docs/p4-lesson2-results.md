# Project 4 — Lesson 2: Bounded Orchestration

## Scope

A synthetic workflow validates requests, authorizes the entire tool
plan, enforces a three-operation limit, retrieves fixture evidence,
and generates a review draft.

No AWS API calls, model calls, tickets, or resource changes occur.

## Observed validation

- Seven workflow scenarios passed.
- Six orchestration unit tests passed.
- Six lesson 1 baseline unit tests passed.
- Unauthorized and mixed unauthorized plans dispatched zero tools.
- Plans exceeding three operations dispatched zero tools.
- A simulated retrieval failure stopped the workflow after one attempt.

## Limitations

Plans and audience labels are supplied by synthetic fixtures.
This does not demonstrate authenticated authorization, model-generated
planning, real network timeout enforcement, or production recovery.

## Next lesson

Add bounded retries and distinguish temporary, permanent, and
malformed tool failures.
