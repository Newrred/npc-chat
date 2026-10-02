"""Offline notice inventory, not a legal clearance or a complete SBOM."""
import argparse
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import shutil
import subprocess


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inside(root, path):
    relative = path.relative_to(root)
    cursor = root
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink() or cursor.is_junction():
            raise ValueError('Linked files are not allowed in notice inputs')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Notice path escapes package')
    return relative.as_posix()


def normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def source_revision(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    try:
        return {'commit': git('rev-parse', 'HEAD'), 'dirty': bool(git('status', '--porcelain'))}
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'dirty': None}


def collect(package, output, lock, provenance=None):
    package, output = package.resolve(), output.absolute()
    if not package.is_dir():
        raise ValueError('Package folder missing')
    if output.exists():
        raise ValueError('Notice output already exists; choose a new folder')
    if output.is_symlink() or output.resolve() == package or package.is_relative_to(output.resolve()):
        raise ValueError('Unsafe notice output')
    if any(p.is_symlink() or p.is_junction() for p in (output, *output.parents)):
        raise ValueError('Linked notice output is not allowed')
    expected = {}
    for line in lock.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        name, version = line.strip().split('==')
        key = normalized(name)
        if key in expected:
            raise ValueError('Duplicate locked package')
        expected[key] = version
    report = {'format': 1, 'distribution': 'internal-test-only', 'release_allowed': False,
              'source': provenance or {'commit': None, 'dirty': None}, 'lock_sha256': sha256(lock),
              'limitations': ['Metadata and notice inventory only; not a complete transitive SBOM',
                              'Rights review, upstream artifact provenance and release approval remain pending'],
              'issues': ['release_review_pending'], 'python': [], 'notices': [], 'artifacts': []}
    site = package / 'runtime/python/Lib/site-packages'
    inside(package, site)
    selected = set()
    found = {}
    for dist in sorted(distributions(path=[str(site)]), key=lambda d: d.metadata['Name'].lower()):
        name = dist.metadata['Name']
        key = normalized(name)
        if key in found:
            raise ValueError('Duplicate installed package')
        found[key] = dist.version
        files = []
        for f in dist.files or []:
            if any(part.lower().startswith(('license', 'copying', 'notice')) for part in Path(f).parts):
                path = Path(dist.locate_file(f)).absolute()
                rel = inside(package, path)
                if path.is_file():
                    files.append(rel)
                    selected.add(path)
        declared = dist.metadata.get('License-Expression') or '; '.join(
            c.split(' :: ')[-1] for c in dist.metadata.get_all('Classifier', []) if c.startswith('License ::'))
        report['python'].append({'name': name, 'version': dist.version,
                                 'declared_license': declared or 'unspecified', 'notices': sorted(files),
                                 'review': 'pending'})
        if not files:
            report['issues'].append('python_notice_missing:' + key)
    for name in sorted(set(expected) | set(found)):
        if expected.get(name) != found.get(name):
            report['issues'].append('python_lock_mismatch:' + name)
    # Walk only the packaged runtime and publish root; never scan developer data.
    roots = [package, package / 'runtime/python', package / 'runtime/llama', package / 'runtime/webview2']
    for root in roots:
        candidates = root.iterdir() if root == package and root.exists() else root.rglob('*')
        for path in candidates:
            if path.name.lower().startswith(('license', 'notice', 'copying', 'third-party', 'thirdparty')) and path.suffix.lower() in ('', '.txt', '.md', '.rst', '.html'):
                inside(package, path)
                if path.is_file():
                    selected.add(path)
    for group, rel in [('python', 'runtime/python/python.exe'), ('dotnet-app', 'NpcChat.Desktop.dll'),
                       ('llama', 'runtime/llama/llama-server.exe'), ('webview2', 'runtime/webview2/msedgewebview2.exe'),
                       ('model', 'models/model.gguf')]:
        path = package / rel
        inside(package, path)
        if path.is_file():
            report['artifacts'].append({'component': group, 'path': rel, 'sha256': sha256(path),
                                        'upstream_revision': None, 'review': 'pending'})
        else:
            report['issues'].append('artifact_missing:' + group)
    for group, prefix in [('python', 'runtime/python/'), ('llama', 'runtime/llama/'), ('webview2', 'runtime/webview2/')]:
        if not any(p.relative_to(package).as_posix().startswith(prefix) for p in selected):
            report['issues'].append('notice_group_missing:' + group)
    report['issues'] += ['dotnet_notices_review_pending', 'cuda_notices_review_pending',
                         'webview2_terms_review_pending', 'model_rights_pending', 'character_assets_rights_pending']
    # All validation happens before writing. Existing output is never merged/overwritten.
    output.mkdir(parents=True, exist_ok=False)
    lines = ['# Third-party notice inventory', '', 'INTERNAL TEST ONLY — redistribution review pending.',
             'This index does not replace the original notices or establish permission to distribute.', '']
    for path in sorted(selected):
        rel = inside(package, path)
        target = output / 'files' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        record = {'package_path': rel, 'notice_path': 'files/' + rel, 'sha256': sha256(target)}
        report['notices'].append(record)
        lines.append('- [' + rel + '](' + record['notice_path'] + ')')
    lines += ['', '## Unresolved items', *('- ' + issue for issue in report['issues'])]
    (output / 'THIRD-PARTY-NOTICES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (output / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def enforce_distribution(mode):
    if mode != 'internal':
        raise ValueError('Release distribution is disabled until rights and provenance review is implemented and completed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.package, args.output, args.lock)
    print(json.dumps({'notices': len(report['notices']), 'python': len(report['python']),
                      'release_allowed': report['release_allowed'], 'issues': report['issues']}))
