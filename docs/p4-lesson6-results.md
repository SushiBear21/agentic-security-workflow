# Project 4 — Lesson 6: CI and Regression Checks

## Workflow evidence

https://github.com/SushiBear21/agentic-security-workflow/actions/runs/40991442915

## Verified evidence

- The CI manifest contains the Git revision and source/report hashes.
- The downloaded lesson 5 comparison reports offline_simulation.
- The comparison is complete.
- Actual model calls attempted: zero.

## Automated checks

The workflow runs the 36 lesson unit tests, 53 reference evaluation
checks, and a negative control that must reject the broken baseline.

It verifies report counts, expected outcomes, and zero model calls.
It retains the generated evidence artifact for 14 days.

## Scope

The workflow evaluates the inline Project 4 companion.
Live model evaluation remains separate.
Human narrative review and configuration selection remain pending.

## Next lesson

Complete human review and map evidence to AI governance controls.
