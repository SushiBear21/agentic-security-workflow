# Defensive local MCP identity and authorization exercise

**Harmless, local/CI-only security lab. No actual customer data, privileged systems, cloud changes or commercial IAM integration.**

## Reused portfolio components

- The existing bounded-agent action hash in [app/workflow.py](../../app/workflow.py) is reused via its canonical digest function.
- The role separation and maximum TTL in [tower/access_demo.py](../../tower/access_demo.py) supply the principal policy. The new server **does not** trust a client-supplied role.
- The exercise extends the existing [privileged access demo](../privileged-access-demo.md) with a minimal server-side MCP tool interface and HMAC-signed short-lived identity credentials.
- The separate [Secure Enterprise RAG authorization layer](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/app/authorization.py) illustrates the complementary data retrieval authorization boundary; it is not imported or deployed by this local server.

## Threat model and scope

An untrusted tool-using AI client could attempt to read unauthorized evidence, create tickets without approval, impersonate a privileged user, replay an approval, reuse an expired credential, or modify a request after approval. The local MCP server has no filesystem mutation, subprocess execution, shell, network client or backend API. Its only two MCP tools are:

| Tool | Server role and scope | Behavior |
| --- | --- | --- |
| evidence.read | requester or executor role with evidence:read | Read one strictly allowlisted in-memory fictional finding |
| ticket.create | executor role with ticket:create plus distinct human-simulator approval | Write one in-memory fictional ticket, bound to exact actor/tool/arguments |

The server rejects any other tool, extra parameters or unknown fixture ID. Credentials are HMAC-SHA256 signed by a process-local random key, audience-bound, scoped, and short lived (1–300 seconds). Neither the signing key nor the raw token is written to the audit trail. Credential issuance and approval are **trusted test-harness calls**, never MCP tools. The approval record binds actor, tool, canonical arguments SHA-256, separate approver, expiration and single-use state. Mutation or replay fails closed. The audit stores an actor, tool, authorization outcome, request digest, approval reference and result, not credentials.

This is **not** an OAuth authorization server, mTLS deployment, multi-tenant authentication system, enterprise vault or independently signed human review. The STDIO fixture passes the signed credential in a lab-specific MCP request _meta field to demonstrate server-side verification. This is not a standard production transport authentication profile and should not be used to send real bearer tokens through model-visible tool arguments. HTTP MCP deployments must use the protocol's OAuth resource-server rules, valid token audiences and strong client authentication. See [MCP 2025-06-18 authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) and [MCP 2025-11-25 authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), including token-passthrough prohibitions. The lab intentionally pins a minimal 2025-06-18 STDIO tool protocol rather than claiming complete support for newer revisions or SDK interoperability.

## Run and inspect

    python -m tower.mcp_identity_lab --output mcp-demo.json
    python -m unittest discover -s tests -p 'test_ai_governance_mcp_lab.py' -v

The module also implements a minimal stdio JSON-RPC MCP server interface:

    python -m tower.mcp_identity_lab --stdio

It handles initialize, notifications/initialized, ping, tools/list and tools/call. Only tests or a trusted local harness can provision a fixture credential/approval; this executable does not expose a credential-issuance/approval tool to an AI client. The server emits one JSON object per line on stdout, with no network exposure.

## Exercise paths and expected outcomes

| Scenario | Expected | Security reason |
| --- | --- | --- |
| Read permitted synthetic evidence | ALLOW | Signed actor and scoped evidence:read |
| Read unlisted fixture | DENY | Resource allowlist |
| Request ticket with reader identity | DENY | Server-owned role + per-tool permission |
| Use expired token | DENY | Verified exp, iat and audience |
| Execute without approval | DENY | High-impact action requires unconsumed exact request approval |
| Execute with distinct approver approval | ALLOW | Exact digest, valid actor, role, expiry and one-time use |
| Alter arguments after approval | DENY | SHA-256 request mismatch |
| Replay approval | DENY | Approval consumed before ticket creation |
| Wrong audience, modified signature, unknown tool or extra params | DENY | Fail-closed validation |

The actual local test implementation covers these scenarios, secret redaction and the minimal MCP handshake. The CI workflow reruns them against the checkout and uploads a synthetic output artifact. Do not claim remote system security, OAuth token exchange, distributed concurrency or production human approval from these tests. Reviewer and approver names in all artifacts are synthetic roles. Azure remains parked.

## Audit example

Each record contains seq, synthetic, actor, tool, authorization_decision, approval_id, request_sha256, and result. No password, raw bearer credential or signing key belongs in this record. The read-only audit list in this exercise is process-memory evidence; a production system would require append-only protected storage, trusted timestamping, retention and access controls.

## Security and testing limitations

The server uses a memory lock to serialize approval consumption, but it is a single-process demonstration with no persistent replay protection after restart. It does not enforce external identity proofing, credential revocation, independent human reviewer authenticity, production session binding, OAuth/JWT verification or downstream service permissions. Its ticket side effect is harmless and in-memory. The generated output is a negative-control demonstration, not a certification.
