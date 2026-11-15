# Selected-control FedRAMP readiness evidence exercise

**Synthetic lab only; not a FedRAMP package submitted for authorization, an SSP, a 3PAO assessment, an ATO or a certification.** This exercise organizes selected NIST SP 800-53 Rev. 5 evidence and gaps. It does not establish full coverage of any FedRAMP baseline, parameter values or enhancement requirements.

## Boundary and inventory

Boundary: local Python Control Tower, its SQLite fixture store, static exported evidence and a simulated privileged-access module. No customer data, CUI, FTI, PII or federal information is processed. Six synthetic security/vendor findings are the input inventory. Local Python and the operating system are dependencies; code repository and operator workstation administration sit outside the demonstration's enforcement boundary. Optional historical AWS resources are **not assessed by this package**.

## Evidence method

Run `python -m tower.readiness_package --output <new-directory>` from the repository root. This creates a source-evidence manifest, copies selected source/test/doc evidence, includes the mapping and gap register, and calculates SHA-256 hashes. Then run `python -m tower.readiness_package --verify <directory>` to detect missing, altered or unexpected package files. Hashes do not prove provenance, identity, completeness or immutability. Package generation is not proof that tests passed: see the separate validation record and run the tests yourself.

Review sequence: establish scope and applicable baseline, inspect each selected control and implementation claim, inspect tests and results, identify missing production evidence, assign remediation owners, then obtain independent review. A real authorization project would require an agency sponsor and applicable FedRAMP process, complete SSP, parameterization, inventories, assessment plan/results, continuous monitoring and assessor engagement. This exercise supplies none of those approvals.

## Selected NIST references and evidence

See `readiness-controls.json` for machine-readable records, bounded implementation assertions, gaps and evidence paths. These are **partial demonstration mappings**, never “compliant” scores.

| Control | Demonstrated aspect | Material gap |
|---|---|---|
| AC-3 Access Enforcement | Local action/resource allowlist and denied operations | No authenticated production principal or operating-system enforcement |
| AC-5 Separation of Duties | Distinct simulated requester and approver | One OS operator can impersonate both personas |
| AC-6 Least Privilege | Only one bounded synthetic action/resource combination | No deployed IAM policy validation or actual privileged session |
| AU-2 Event Logging | Approval/execution/denial events | Organizational event policy and production telemetry absent |
| AU-3 Content of Audit Records | Actor, action, decision and payload references | Actor is simulated, not verified identity |
| AU-9 Protection of Audit Information | Hash-based modification detection | Administrator can rewrite chain and evidence; no immutable retention |
| CA-7 Continuous Monitoring | Repeatable checks and evidence refresh procedure | No production cadence, owner accountability or continuous service |
| CM-3 Configuration Change Control | Versioned source and reviewable change set | No independent release approver or production change board |
| RA-5 Vulnerability Monitoring and Scanning | Synthetic findings mapped and tracked | No scanner coverage or actual vulnerability assessment |
| SI-2 Flaw Remediation | Evidence-gated synthetic ticket closure | No actual patch deployment or validation |

Authoritative reference: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final . Applicable FedRAMP requirements must be checked at https://www.fedramp.gov/ before real use. These references are background standards, not endorsements.

## Illustrative POA&M-style gap register

This is a lab planning register, not the official FedRAMP POA&M template or a finding from an assessor. Owner roles and relative milestones are proposed, not real assigned commitments.

| ID | Gap / risk | Proposed owner | Exit criterion | Relative milestone |
|---|---|---|---|---|
| LAB-01 | Caller-selected personas undermine identity separation | Identity engineer | External authenticated identities, isolated approver roles and denial tests | Before live access demo |
| LAB-02 | Editable local evidence cannot resist privileged rewriting | Security engineer | Independently controlled retention and verification source | Before assurance claim |
| LAB-03 | Selected controls are incomplete | Compliance lead | Applicable baseline/enhancements/parameters and full evidence matrix reviewed | Before readiness review |
| LAB-04 | AI quality gate failed | AI program lead | Prespecified held-out independent review meets release criteria | Before AI release |
| LAB-05 | Production scans, incident exercises and cloud privilege tests absent | Security operations | Authorized live evidence and assessor review | Before production assessment |

No gap is marked remediated solely by adding this document. The package deliberately records these limits.
