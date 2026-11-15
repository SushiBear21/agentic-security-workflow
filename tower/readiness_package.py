"""Offline selected-control evidence pack. No cloud calls or compliance verdict."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'tower/core.py', 'tower/store.py', 'tower/report.py', 'tower/access_demo.py',
    'tower/readiness_package.py', 'tower/fixtures.json', 'tests/test_readiness_package.py',
    'tests/test_tower.py', 'tests/test_access_demo.py',
    'docs/control-tower.md', 'docs/p4-final-results.md',
    'docs/privileged-access-demo.md', 'docs/portfolio/ai-program-delivery-case-study.md',
    'docs/portfolio/fedramp-readiness-lab.md', 'docs/portfolio/readiness-controls.json',
    'docs/portfolio/extension-validation.md',
    'tower/assurance.py', 'tower/release.py', 'p4_regression.py',
    'requirements.txt', 'Dockerfile', 'tests/fixtures/p4-regression-v1.json',
    'tests/test_assurance.py', 'tests/test_release.py', 'tests/test_access_extensions.py',
    'tests/test_uncertain_outcome.py', 'tests/test_regression_gate.py',
    'docs/portfolio/customer-deployment.md', 'docs/portfolio/assurance-workflow.md',
    'docs/portfolio/evaluation-extensions.md',
    'Dockerfile.service', 'tower/adoption.py', 'tower/compliance.py',
    'tower/deploy.py', 'tower/service.py', 'tower/aws_evidence.py',
    'tests/test_adoption.py', 'tests/test_compliance.py', 'tests/test_deploy.py',
    'tests/test_aws_evidence.py', 'tests/fixtures/adoption-v1.json',
    'docs/portfolio/synthetic-ssp.md', 'docs/portfolio/poam.json',
    'docs/portfolio/monitoring-plan.json', 'docs/portfolio/deployment-automation.md',
    'docs/portfolio/adoption-measurement.md', 'docs/portfolio/continuous-monitoring.md',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative(name):
    path = Path(name)
    if not isinstance(name, str) or not name or path.root or path.drive or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('Unsafe evidence path')
    return path


def build(destination):
    out = Path(destination)
    if out.exists():
        raise ValueError('Use a new output directory; existing evidence is not overwritten')
    # Validate every input before creating a partial package.
    for name in FILES:
        if not (ROOT / name).is_file():
            raise ValueError('Missing source evidence: ' + name)
    out.mkdir(parents=True)
    for name in FILES:
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    manifest = {
        'schema_version': 1,
        'classification': 'synthetic_lab_selected_controls_only',
        'assertion': 'Not FedRAMP authorization, certification, full baseline coverage or proof of test execution',
        'files': {name: digest(out / name) for name in FILES},
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    verify(out)
    return manifest


def verify(directory):
    root = Path(directory)
    manifest_path = root / 'manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('Symlink manifest')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or manifest.get('classification') != 'synthetic_lab_selected_controls_only':
        raise ValueError('Unexpected manifest schema or classification')
    files = manifest.get('files')
    if not isinstance(files, dict) or set(files) != set(FILES):
        raise ValueError('Unexpected evidence inventory')
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Symlink evidence')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(FILES) | {'manifest.json'}:
        raise ValueError('Missing or unexpected files')
    for name, expected in files.items():
        path = root / safe_relative(name)
        if digest(path) != expected:
            raise ValueError('Evidence hash mismatch: ' + name)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output')
    group.add_argument('--verify')
    args = parser.parse_args()
    if args.output:
        build(args.output)
    else:
        verify(args.verify)
    print('PASS: synthetic evidence inventory and hashes verified; no compliance verdict')


if __name__ == '__main__':
    main()
