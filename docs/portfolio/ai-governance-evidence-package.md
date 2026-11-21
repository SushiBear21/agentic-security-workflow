# Synthetic AI governance evidence package — independent portfolio lab

**INDEPENDENT SYNTHETIC PORTFOLIO WORK. NOT COMMERCIAL AI GOVERNANCE OWNERSHIP, PRODUCTION READINESS, CERTIFICATION, OR AN OFFICIAL NIST ASSESSMENT.**

## Purpose, boundaries and components

This package extends the existing [bounded agent workflow](../../app/workflow.py), [privileged-access simulation](../../tower/access_demo.py), [release evidence logic](../../tower/release_record.py), and [Control Tower AI RMF demonstration](../../tower/governance.py). It cross-references the separate [Secure Enterprise RAG repository](https://github.com/SushiBear21/secure-enterprise-rag) including [verified-group audiences](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/app/authorization.py) and [pre-model retrieval boundary tests](https://github.com/SushiBear21/secure-enterprise-rag/blob/main/tests/security/test_retrieval_boundary.py). The cross-repository reference demonstrates reuse of security design, **not proof of operation of a commercial customer environment**.

The fictional system handles only dummy security findings and in-memory ticket proposals. The package makes no AWS/Azure calls, uses no actual CUI or customer information, deploys no model, and cannot authorize production actions. All identified owners, human approvals, incidents and monitoring samples in the new package are fictional.

## Generate a reproducible no-go packet

From the repository root:

    python -m unittest discover -s tests -p 'test_ai_governance_mcp_lab.py' -v
    python -m tower.mcp_identity_lab --output mcp-demo.json
    python -m tower.ai_governance_evidence --output governance-evidence-new

Use a **new output directory**; existing evidence cannot be overwritten by the generator. For the intended hosted validation, see [GitHub Actions](../../.github/workflows/ai-governance-mcp.yml). Never commit real credential tokens: the demo returns only decisions, actor IDs, tool IDs, request digests, approval IDs and results. The generator retains SHA-256 hashes of all ten substantive JSON files in an evidence manifest. Timestamps in fixture metrics are fixed authored scenario times, not live operational telemetry.

## Artifact-to-framework traceability

| AI RMF function | Illustrative subcategories | Output evidence | What it proves / does not prove |
| --- | --- | --- | --- |
| GOVERN | 1.1, 1.3, 1.4, 2.1 | system_card, evaluation_criteria, risk_register, approval_decision | Identifies obligations, thresholds, owners, independent roles; not actual board sign-off |
| MAP | 1.1, 2.1, 5.1 | system_card, risk_register | Documents intended use, stakeholder impacts, threats and prohibited uses |
| MEASURE | 1.1, 2.1, 3.1 | evaluation_criteria, evaluation_results, monitoring | Local fixture results with six explicit test cases; telemetry is an authored fixture |
| MANAGE | 1.1, 2.1, 4.1 | release_decision, risk_register, monitoring | Deterministic withholding of release on unverified or failed gates |

The machine-readable crosswalk is in the generated **rmf_mapping.json**, with requirement IDs, control narrative and evidence filename. NIST AI RMF 1.0 is voluntary guidance, not a compliance certification. Refer to the [NIST AI RMF core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) and [NIST playbook](https://airc.nist.gov/airmf-resources/playbook/). The NIST playbook currently notes AI RMF 1.0 is being updated, so reconfirm changes before using these mappings beyond this time-stamped exercise.

## System/model card and evaluation criteria

**system_card.json** identifies the intended advisory use, users, synthetic input sources, architectural dependencies, human decision points, and prohibited uses. There is **no model invocation** in this new lab: model provider/version, live performance, trained data and fairness metrics are explicitly unknown. That prevents local deterministic tests from being mistaken for live Bedrock model quality.

**evaluation_criteria.json** prescribes the six MCP decision outcomes before evaluation, requires all to pass, and separately requires independent model holdout, source-based human review, exact-revision security scans and monitoring before any lab GO. **evaluation_results.json** contains each expected/actual outcome, model-call count (zero), and primary local audit. These six checks must not be confused with the historical **6/6 Bedrock holdout and 4/4 independent human review** described in the existing [customer deployment narrative](customer-deployment.md#approved-bedrock-holdout-lab-release). That narrative and a [related container CI run](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44171202837) were examined. The complete, origin-verifiable holdout/reviewer artifacts have **not** been independently validated in this new packet, so neither claim is imported as a verified release gate.

## Risks, approvals and reporting

The **risk_register.json** has six fictional risks with severity, accountable owners, treatment proposals, outstanding evidence and AI RMF mappings. Unaccepted HIGH risks block release. The **mcp_identity_audit.json** demonstrates trusted role differentiation, short-lived scoped tokens, server-side per-tool checks, and exact-request high-impact approval with no raw credentials retained. The approval uses a separate fictional approver, not a real independent person.

The **approval_decision.json** deliberately records **WITHHELD** because no real independent human governance review occurred. **release_decision.json** is strictly fail closed: missing holdout, independent review, image/dependency scan, monitoring freshness, unresolved high risks, alert AL-01, or exact-manifest independent authorization => **NO_GO**. The test suite also demonstrates a *hypothetical* **LAB_GO** when every simulated gate is true, high risks and alerts are resolved, and a separate authorized actor approves the matching digest. In all scenarios **production_authorized=false**.

The authored fixture records 8 failures per 100 requests, above a predefined 5% threshold, to exercise a real algorithmic alert condition. This is **not an observed failure rate**, and the generated management report states it explicitly. **scan_results.json** marks actual vulnerability scanning **NOT_VERIFIED** until CI produces its own scanner results; do not treat source code examination as a dependency/image scan. The separate CI job runs pip-audit on pinned Python dependencies and Bandit SAST on the two new Python modules, retaining the raw JSON reports and failing on scanner findings. Neither scan establishes container-image safety or qualifies an AI release.

## Verified tests and limits

The initial code was locally exercised with Python's unittest runner, giving **15 passing tests** against a local copy of the new logic and compatible stubs for existing digest and role constants. **November 21, 2026 GitHub Actions run [44935910349](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44935910349) passed 13 committed tests, validated the generated NO_GO evidence and ten-file manifest, and passed the MCP STDIO handshake.** The same workflow's dependency-scan job completed successfully with **no known vulnerabilities found** for the pinned requirements.txt packages, and retained a [dependency audit artifact](https://github.com/SushiBear21/agentic-security-workflow/actions/runs/44935910349). These tests and the dependency report do **not** independently validate the historical 6/6 Bedrock or 4/4 human review claims, do not scan a built container image for this candidate, and do not authorize release.

This package intentionally does not inherit old sandbox pass results into a new release, does not collect real production telemetry, cannot verify user identity, does not issue official approvals, and has no Azure dependencies. Its practical value is a traceable, reviewable **NO_GO** with explicit remediation evidence rather than a fabricated green compliance or deployment assertion.

## Management handoff

The simulated board should withhold this candidate until raw current holdout artifacts and independent human review are verifiable, CI scan findings are addressed for the exact revision, monitoring evidence is real/fresh, all HIGH risk decisions are documented and accepted or remediated, and a distinct authorized reviewer signs the exact candidate evidence manifest. A commercial deployment would additionally need operational design reviews, privacy/data contracts, service ownership and actual authority.
