"""Digest-pinned synthetic model release preflight. Never loads model weights."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/model_supply"
POLICY = ROOT / "tower/model_supply_policy.json"
RAG_REV = "6b45c18fa58b498b3b1714529cfded8b5bc5648b"
RAG_BLOBS = {
    "requirements.txt": "c8d0a28a199cbfbf24a1351d05974532a53eb960",
    "app/rag_service.py": "734ee052e5ac3da74fbe44f2f487dc4eb74eea45",
    "infra/terraform/knowledge-base.tf": "58adceacff0f20287e595c1a9be3d19467bd85f5",
}
MODEL_ID = "amazon.nova-lite-v1:0"
EMBEDDING_ID = "amazon.titan-embed-text-v2:0"


class Rejected(ValueError):
    """A failed gate; use fixed reason codes, not untrusted input in evidence."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(root, name):
    root = Path(root)
    path = root / name
    if (root.is_symlink() or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
            or not path.is_file() or path.stat().st_size > 65536):
        raise Rejected("missing_or_unsafe_file")
    return path.read_bytes()


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise Rejected("duplicate_manifest_key")
        result[k] = v
    return result


def decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise Rejected("invalid_manifest") from None


def policy():
    return decode(POLICY.read_bytes())


def dependency_inventory(raw, expected):
    if digest(raw) != expected:
        raise Rejected("unapproved_dependency_lock")
    entries = []
    seen = set()
    for line in raw.decode("ascii").splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9.+!-]+)", line)
        if not match:
            raise Rejected("invalid_dependency_pin")
        name, version = match.groups()
        name = re.sub(r"[-_.]+", "-", name).lower()
        if name in seen:
            raise Rejected("duplicate_dependency")
        seen.add(name)
        entries.append({"type": "library", "name": name, "version": version,
                        "purl": "pkg:pypi/" + name + "@" + version})
    if not entries:
        raise Rejected("empty_dependency_lock")
    return entries


def verify_bundle(bundle, release, rag_lock):
    """Verify candidate bytes against a separately reviewed Git-pinned policy.
    A manifest supplied by the candidate cannot expand the trust policy.
    """
    p = policy()
    if release not in p["releases"]:
        raise Rejected("unapproved_release")
    expected = p["releases"][release]
    raw = read(bundle, "manifest.json")
    manifest = decode(raw)
    if not isinstance(manifest, dict):
        raise Rejected("invalid_manifest")
    if manifest.get("origin") != p["approved_origin"]:
        raise Rejected("unapproved_origin")
    if manifest.get("rag_lock_sha256") != p["rag_lock_sha256"]:
        raise Rejected("unapproved_dependency_lock")
    # Compare canonical JSON, including types (True must not equal 1).
    if json.dumps(manifest, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise Rejected("manifest_not_in_policy")
    components = dependency_inventory(rag_lock, p["rag_lock_sha256"])
    for entry in expected["artifacts"]:
        raw_artifact = read(bundle, entry["name"])
        if digest(raw_artifact) != entry["sha256"]:
            raise Rejected("artifact_digest_mismatch")
    return {"status": "pass", "release": release,
            "manifest_sha256": digest(raw), "policy_sha256": digest(POLICY.read_bytes()),
            "artifacts": expected["artifacts"], "origin": expected["origin"],
            "rag_lock_sha256": p["rag_lock_sha256"], "dependency_components": components}


def verify_rag(root):
    # Check exact public repository revision and exact relevant working-tree bytes.
    ref = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                  text=True).strip()
    if ref != RAG_REV:
        raise Rejected("rag_revision_mismatch")
    content = {}
    for name, expected in RAG_BLOBS.items():
        raw = read(root, name)
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != expected:
            raise Rejected("rag_source_mismatch")
        content[name] = raw
    if (MODEL_ID.encode() not in content["app/rag_service.py"]
            or EMBEDDING_ID.encode() not in content["infra/terraform/knowledge-base.tf"]):
        raise Rejected("rag_provider_id_mismatch")
    return content["requirements.txt"], {
        "revision": ref, "source_sha256": {k: digest(v) for k, v in content.items()},
        "configured_inference_id": MODEL_ID, "configured_embedding_id": EMBEDDING_ID,
        "weight_verification": "unavailable: provider-managed models; identifiers only",
    }


def rehearse(rag_lock):
    stable = verify_bundle(FIXTURES / "stable", "stable", rag_lock)
    candidate = verify_bundle(FIXTURES / "candidate", "candidate", rag_lock)
    active = stable
    active = candidate  # mock release pointer, no actual deployment
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "candidate"
        shutil.copytree(FIXTURES / "candidate", target)
        (target / "model.txt").write_bytes(b"benign altered fixture\n")
        try:
            verify_bundle(target, "candidate", rag_lock)
        except Rejected as error:
            if str(error) != "artifact_digest_mismatch":
                raise
            denial = str(error)
        else:
            raise AssertionError("Altered candidate accepted")
        # Re-verify previous bytes under the current policy before restoring.
        restored = verify_bundle(FIXTURES / "stable", "stable", rag_lock)
        if restored != stable:
            raise Rejected("rollback_receipt_mismatch")
        active = restored
    return {"scope": "synthetic model release preflight only", "status": "pass",
            "initial": stable, "approved_candidate": candidate,
            "injected_failure": denial, "restored": active,
            "rollback_verified": active == stable,
            "owner_approval": "pending; policy fixture is not an authenticated human decision",
            "exceptions": [], "production_authorized": False, "live_model_calls": 0}


def model_sbom(receipt):
    # Extend the repository's existing installed Python pin SBOM, not a new
    # dependency scanner. RAG dependencies are a separate declared inventory.
    from tower.release import sbom
    installed = sbom()
    manifest = receipt["approved_candidate"]
    model_components = [
        {"type": "file", "name": entry["name"], "version": entry["version"],
         "hashes": [{"alg": "SHA-256", "content": entry["sha256"]}],
         "properties": [{"name": "portfolio:scope", "value": "inert synthetic model fixture"}]}
        for entry in manifest["artifacts"]
    ]
    installed["components"] += model_components
    installed["metadata"]["properties"].append({
        "name": "portfolio:model_scope",
        "value": "Installed agentic Python pins plus synthetic candidate model and embedding; not container or provider weight inventory",
    })
    return installed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rag-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    lock, rag = verify_rag(args.rag_root)
    receipt = rehearse(lock)
    receipt["rag"] = rag
    receipt["code_revision"] = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    sbom = model_sbom(receipt)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in (("model-sbom.json", sbom), ("model-supply.json", receipt)):
        (args.output / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    checksums = {p.name: digest(p.read_bytes()) for p in sorted(args.output.iterdir())}
    (args.output / "sha256.json").write_text(json.dumps(checksums, indent=2) + "\n")
    print("Synthetic preflight passed; candidate rejected after tamper; stable reverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
