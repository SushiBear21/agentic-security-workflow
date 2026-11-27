# Synthetic model supply chain preflight (#33)

## Trust boundary and procedure

This adds a **blocking preflight to the existing offline Portfolio extension evidence workflow**; subsequent existing dependency audit, container build, rollback and assurance still apply. The separate Container security workflow continues to generate actual container CycloneDX SBOMs and Trivy reports and validate scan/image binding; the existing `tower.release_record` independently handles digest-bound human quality/release approval. No staging publish or ECS deploy workflow is changed. No cloud API calls are made. The secure RAG repository is consumed at the exact reviewed commit `6b45c18fa58b498b3b1714529cfded8b5bc5648b`; no RAG core files or other branches are modified.

Trust anchor: protected/reviewed checkout of `tower/model_supply_policy.json` and the three pinned RAG Git blob identities. Candidate bundles cannot self-authorize a different origin, model or dependency digest. The manifest is verifiable against the independently supplied policy and bytes, not a digital signature; no key, signer identity, transparency log or external attestation is asserted. The policy and candidate fixtures share a repository and an actor with policy-write rights could modify both. Independent policy review, protected rules and separate custody are not established. Do not ingest arbitrary model files, unpickle or execute model bytes.

Inventory covers inert text model/embedding v1 and v2 release fixtures, origin/owner/license and SHA-256, RAG's configured Nova/Titan IDs and declared locked Python dependencies, and existing installed agentic Python pins. Managed Bedrock weight bytes and provider provenance are unavailable; model IDs do not prove weight identity, safety or integrity. The extended CycloneDX inventory is not an OS/container SBOM; use the existing container workflow's actual image SBOM and scan records separately. These model fixtures are not packaged into a real model-serving image. No inference, production deployment, scanner pass or external model safety claim follows from this gate.

## Reproduce locally

From a clean checkout with Python 3.13, run:
```sh
python -m unittest discover -s tests -p test_model_supply.py -v
git clone https://github.com/SushiBear21/secure-enterprise-rag.git ../rag-supply-source
git -C ../rag-supply-source checkout --detach 6b45c18fa58b498b3b1714529cfded8b5bc5648b
python -m pip install -r requirements.txt
python -m tower.model_supply --rag-root ../rag-supply-source --output model-supply-evidence
```
Use a new output directory each run. The CLI verifies the RAG Git HEAD and actual working-tree bytes. It builds the candidate fixture receipt and attempts a benign modified model in a temporary directory, denies it, then re-verifies the previous stable bundle before restoring a mock active pointer. It does not roll back real infrastructure. The receipt includes code SHA, RAG SHA and per-file hashes, model/embedding/dependency digests, separate RAG declared dependencies, no exceptions, pending owner approval and explicit no-production-authorization. Verify `sha256.json` against the exported JSON bytes; archive retention is 30 days in CI. Run the existing offline and container workflows to obtain the remaining independent release evidence.

## Selected control analogues (not assessment or certification)

| Control | Lab evidence | Remaining gap |
|---|---|---|
| AI RMF GOVERN 6.1, MAP 4.1 | Registry and origin/license/owner, dependency inventory | Human supplier review, contracts and actual provenance |
| AI RMF MEASURE 2.7, MANAGE 4.1 | Integrity negatives, denied candidate and mock rollback receipt | Adversarial model testing and operating incident/recovery evidence |
| SSDF PS.2, PS.3, PW.4 | Hash-pinned manifests, pinned source and package inventory, existing CI SBOM/scan | Signed external provenance, separate custody and continuous supplier verification |
| SP 800-53 Rev. 5 SR-4, SR-11, SI-7, CM-3, CP-10 | Registry, exact bytes, fail-closed change and recovery | Actual component authenticity, production change approval and recovery testing |

Cross-reference #19 / PR #27 governance evidence and #9 / #17 release controls. Do not change existing approval semantics or claim a policy fixture is a real owner's decision. Owner approval and independent review: pending. No exceptions approved. Residual risks: untrusted supplier, compromised build/policy maintainer, unmeasured transitive/OS exposure, provider-managed weights, stale pinned revision, no real model safety or behavioral evaluation. Re-review the trust policy before changing RAG revision or model release.
