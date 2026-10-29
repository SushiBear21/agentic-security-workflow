# Agent workflow boundaries

## Goal

Inspect a frozen synthetic Project 2 snapshot and propose a local
review ticket for its highest-scoring candidate.

## Model-visible tools

- list_candidates
- get_candidate
- propose_ticket

The model has no approval tool, executor, shell, arbitrary file reader,
network-fetch tool, email tool, or AWS administration tool.

## Controlled action

Create one local synthetic review-ticket JSON file after human approval.

The application constructs the ticket's authoritative fields.
The model supplies only a candidate identifier and draft justification.

Scores, applicability, owner, and asset identity come from the snapshot.

## Approval

A separate CLI command displays the complete proposal.
The operator approves its exact digest.
Approval expires after 24 hours.

Execution verifies the proposal and approval again.

## Trust model

Untrusted:
- Source text.
- Model output.
- Tool arguments.

Trusted:
- Application code.
- The local operating-system user.
- The files that user controls.

This is not a multi-user enterprise approval service.
A malicious local user who can edit application files or approval records
is outside this demonstration's security boundary.

The model runs through bounded application tools, not an OS sandbox.

## Credentials

The local operator uses the existing AWS SSO profile for Bedrock.
That profile has administrator privileges.

The model-facing tool allowlist limits application behavior.
It does not turn the operator's AWS credentials into a least-privilege
runtime identity.

A separate scoped runtime role would be required before broader deployment.

## Evidence

This workflow uses a frozen snapshot.
It does not claim the evidence is current.
The ticket requires applicability and patch verification.