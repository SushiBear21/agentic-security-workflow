# Privileged-access demonstration (synthetic lab)

This extension uses the existing Control Tower digest and audit-event helpers. It
is an **in-memory authorization simulation**, not a deployed IAM system, PAM
product, federated identity service, or proof of production least privilege.
No credentials are created and no cloud APIs or paid services are called.

## Run

```sh
python -m tower.access_demo
python -m unittest discover -s tests -p 'test_access_demo.py' -v
```

The reproducible fixture uses logical timestamps 100–104 (not observed wall-clock
performance). It requests access, records a denied unapproved execution, approves
as a different modeled principal, returns one synthetic evidence record, and
records denial of replay. Output is JSON with the request and hash-chained events.

## Policy and behavior

- `lab-requester` can request only `read_synthetic_evidence` on
  `lab://evidence/SEC-001`. Wildcards and other resources/actions are rejected.
- `lab-approver` can approve or reject pending requests. Requester cannot approve.
- `lab-executor` can consume an approval; neither requester nor approver can run
  the modeled operation. The action returns a fixture, not a real asset.
- Requests expire 1–300 seconds after creation; approval cannot extend the window.
- Decisions and execution carry the SHA-256 of the exact request, scope, reason,
  requester, creation time and expiry. Mutation causes rejection.
- Rejection is terminal; execution consumes the approval. A process-local lock
  ensures competing threads consume it once. IDs cannot be reused in that object.
- Accepted transitions and ordinary validation denials have chained audit events.
  Invalid non-finite timestamps are rejected before logging because they cannot
  be serialized reliably into the audit record.

## Verification

The focused suite has 15 tests covering the happy path, permission separation,
unknown principals, action/resource limits, TTL limits, expiry and time reversal,
wrong digests, payload mutation, terminal rejection, replay, duplicate IDs,
single-process concurrency, defensive copies, audit edits, invalid commands and
the demonstrator's expected outcomes. See `tests/test_access_demo.py`.

## Boundaries and next validation

Actor labels and the clock are supplied by the caller. Anyone controlling the
local process can impersonate a label or rewrite memory, policy and the audit
chain. There is **no authentication, independent human identity enforcement,
immutable logging, durable persistence, cross-process replay prevention, or
production access grant/revocation**. The hash chain detects an edited recorded
event only when the remainder is not rewritten; it cannot prove completeness or
prevent truncation. Process restart loses all state.

For a production design, identity would need to come from a verified server-side
session; decisions would need independent approvers, a durable atomic consume,
trusted time, externally anchored immutable audit storage, incident procedures,
and explicit runtime IAM restrictions. Those are design gaps, not completed work.
Any such deployment or persistent credentials requires separate authorization.

Illustrative NIST SP 800-53 Rev. 5 associations: AC-3 (access enforcement), AC-5
(separation of duties), AC-6 (least privilege), AU-3 (audit content), AU-9 (audit
protection gaps). These are limited lab mappings, not FedRAMP control satisfaction
or an authorization claim.
