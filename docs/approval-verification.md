# Approval verification

Run ID: 2b48a88c5e704359858adf85b618a044

Observed:
- Real agent produced a pending proposal.
- Unapproved execution was rejected.
- No ticket existed before approval.
- Operator reviewed the complete payload.
- Explicit digest-bound approval was recorded.
- Execution created the approved local ticket.
- Repeated execution reused the same ticket.
- Approval digest matched the payload.
- Run state became EXECUTED.

The model had no approval or execution tool.

This is a local single-operator demonstration.
Approval records rely on the trusted OS account.
The audit file is not immutable or independently signed.