import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.package_notices import collect, enforce_distribution, inside
from scripts.package_desktop import build, write_manifest
from scripts.verify_desktop_package import verify


def fixture_package(tmp_path, notice=True):
    package = tmp_path / 'package'
    dist = package / 'runtime/python/Lib/site-packages/sample-1.0.dist-info'
    dist.mkdir(parents=True)
    (dist / 'METADATA').write_text('Metadata-Version: 2.1\nName: sample\nVersion: 1.0\nLicense-Expression: MIT\n')
    (dist / 'RECORD').write_text('sample-1.0.dist-info/LICENSE,,\n' if notice else '')
    if notice:
        (dist / 'LICENSE').write_text('synthetic test license')
    lock = tmp_path / 'runtime.lock'
    lock.write_text('sample==1.0\n')
    return package, lock


def test_inventory_preserves_original_notices_without_machine_paths(tmp_path):
    package, lock = fixture_package(tmp_path)
    target = package / 'licenses'
    report = collect(package, target, lock, {'commit': 'a' * 40, 'dirty': False})
    assert report['python'][0]['declared_license'] == 'MIT'
    assert len(report['notices']) == 1
    assert 'python_lock_mismatch:sample' not in report['issues']
    assert (target / report['notices'][0]['notice_path']).read_text() == 'synthetic test license'
    assert str(tmp_path) not in json.dumps(report)
    assert report['release_allowed'] is False
    write_manifest(package)
    assert verify(package) == []
    (target / report['notices'][0]['notice_path']).write_text('tampered')
    assert verify(package)


def test_missing_notice_and_mismatched_version_are_reported(tmp_path):
    package, lock = fixture_package(tmp_path, notice=False)
    lock.write_text('sample==2.0\nmissing==1.0\n')
    report = collect(package, tmp_path / 'audit', lock)
    assert {'python_notice_missing:sample', 'python_lock_mismatch:sample',
            'python_lock_mismatch:missing'} <= set(report['issues'])


def test_native_notices_collected_but_license_viewer_not_executed(tmp_path):
    package, lock = fixture_package(tmp_path)
    native = package / 'runtime/llama'
    native.mkdir()
    (native / 'LICENSE-LLVM-OpenMP').write_text('openmp fixture')
    (native / 'show_licenses.bat').write_text('exit 99')
    report = collect(package, tmp_path / 'audit', lock)
    assert len(report['notices']) == 2
    assert any(n['package_path'].endswith('LICENSE-LLVM-OpenMP') for n in report['notices'])


def test_no_overwrite(tmp_path):
    package, lock = fixture_package(tmp_path)
    with pytest.raises(ValueError, match='already exists'):
        collect(package, package, lock)
    assert (package / 'runtime').exists()


def test_metadata_cannot_escape_package(tmp_path):
    package, lock = fixture_package(tmp_path)
    dist = package / 'runtime/python/Lib/site-packages/sample-1.0.dist-info'
    (dist / 'RECORD').write_text('../../../../../LICENSE,,\n')
    (tmp_path / 'LICENSE').write_text('private')
    with pytest.raises(ValueError, match='escapes'):
        collect(package, tmp_path / 'audit', lock)
    assert not (tmp_path / 'audit').exists()


def test_reparse_input_rejected(tmp_path, monkeypatch):
    package, _ = fixture_package(tmp_path)
    monkeypatch.setattr(Path, 'is_junction', lambda self: self.name == 'runtime')
    with pytest.raises(ValueError, match='Linked'):
        inside(package, package / 'runtime/LICENSE')


def test_release_fails_before_output_creation(tmp_path):
    enforce_distribution('internal')
    with pytest.raises(ValueError, match='disabled'):
        build(SimpleNamespace(output=tmp_path / 'new-package', distribution='release'))
    assert not (tmp_path / 'new-package').exists()


def test_duplicate_lock_rejected_before_writing(tmp_path):
    package, lock = fixture_package(tmp_path)
    lock.write_text('sample==1.0\nsample==2.0\n')
    with pytest.raises(ValueError, match='Duplicate'):
        collect(package, tmp_path / 'audit', lock)
    assert not (tmp_path / 'audit').exists()


def test_builder_collects_notices_before_final_manifest(tmp_path, monkeypatch):
    import zipfile
    from scripts import package_desktop as builder
    root = tmp_path / 'repo'
    for name in ['desktop/requirements-runtime.lock', 'desktop/portable-settings.json', 'docs/PORTABLE_DESKTOP.md']:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{}' if name.endswith('.json') else '')
    inputs = tmp_path / 'inputs'
    for name in ['model.gguf', 'llama/llama-server.exe', 'webview/msedgewebview2.exe', 'publish/NpcChat.Desktop.exe']:
        p = inputs / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'synthetic executable or model')
    archive = inputs / 'python.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('python.exe', 'synthetic')
        z.writestr('LICENSE.txt', 'synthetic python license')
    monkeypatch.setattr(builder, 'ROOT', root)
    monkeypatch.setattr(builder, 'PYTHON_SHA256', builder.digest(archive))
    monkeypatch.setattr(builder.subprocess, 'run', lambda *a, **k: None)
    monkeypatch.setattr(builder, 'source_revision', lambda _: {'commit': None, 'dirty': None})
    output = tmp_path / 'built'
    builder.build(SimpleNamespace(output=output, python_zip=archive, model=inputs / 'model.gguf',
                                  llama=inputs / 'llama', webview=inputs / 'webview', publish=inputs / 'publish'))
    assert verify(output) == []
    report = json.loads((output / 'licenses/inventory.json').read_text())
    assert len(report['notices']) == 1 and report['release_allowed'] is False
    assert any(f['path'] == 'licenses/inventory.json' for f in json.loads((output / 'package-manifest.json').read_text())['files'])
