from types import SimpleNamespace
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts.build_installer import build
from scripts.build_installer import download_url


@pytest.mark.parametrize('query', ['', '?usp=sharing', '?usp=drive_link'])
def test_drive_share_link_normalized(query):
    assert download_url('https://drive.google.com/file/d/test_file-123/view' + query) == (
        'https://drive.usercontent.google.com/download?id=test_file-123&export=download&confirm=t')


@pytest.mark.parametrize('url', [
    'https://drive.google.com/file/d/abc/view?token=secret',
    'https://drive.google.com.evil.test/file/d/abc/view?usp=sharing',
    'https://drive.google.com:444/file/d/abc/view?usp=sharing',
    'https://drive.google.com/file/d/abc/view?usp=sharing&extra=value',
])
def test_drive_query_variants_rejected(url):
    with pytest.raises(ValueError, match='HTTPS'):
        download_url(url)


def args(tmp_path, **kw):
    values = dict(output=tmp_path/'out', package=tmp_path/'missing-package', release_id='1.4.0-test',
                  distribution='internal', app_url=None, model_url=None)
    values.update(kw)
    return SimpleNamespace(**values)


def test_release_builder_rejected_before_reading_or_writing(tmp_path):
    with pytest.raises(ValueError, match='disabled'):
        build(args(tmp_path, distribution='release'))
    assert not (tmp_path/'out').exists()


def test_existing_build_output_never_overwritten(tmp_path):
    output = tmp_path/'out'
    output.mkdir()
    sentinel = output/'keep'
    sentinel.write_text('keep')
    with pytest.raises(ValueError, match='new output'):
        build(args(tmp_path))
    assert sentinel.read_text() == 'keep'


@pytest.mark.parametrize('url', ['http://example.test/file', 'https://user:password@example.test/file',
                                'https://example.test/file?token=private', 'https://example.test/file#fragment'])
def test_unsafe_download_source_rejected(tmp_path, url):
    with pytest.raises(ValueError, match='HTTPS'):
        build(args(tmp_path, app_url=url, model_url='https://example.test/model'))
    assert not (tmp_path/'out').exists()


def test_partial_download_configuration_rejected(tmp_path):
    with pytest.raises(ValueError, match='Both'):
        build(args(tmp_path, app_url='https://example.test/app'))
    assert not (tmp_path/'out').exists()


def test_compact_payload_preserves_bytes_and_manifest(tmp_path, monkeypatch):
    from scripts import build_installer

    package = tmp_path / 'package'
    (package / 'models').mkdir(parents=True)
    contents = {'runtime/library.dll': b'repeated binary content' * 10000,
                'NpcChat.Desktop.exe': b'app fixture', 'models/model.gguf': b'model unchanged'}
    records = []
    for name, data in contents.items():
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        records.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (package / 'package-manifest.json').write_text(json.dumps({'format': 1, 'files': records}))

    def collect_stub(_package, output, _lock):
        output.mkdir()
        (output / 'notice.txt').write_text('preserve notices')
        return {'notices': ['notice.txt']}

    def publish_stub(command, **_kwargs):
        output = Path(command[command.index('-o') + 1])
        output.mkdir()
        (output / 'NpcChat.Setup.exe').write_bytes(b'installer fixture' * 100)

    monkeypatch.setattr(build_installer, 'collect', collect_stub)
    monkeypatch.setattr(build_installer.subprocess, 'run', publish_stub)
    build(args(tmp_path, package=package))
    output = tmp_path / 'out'
    with zipfile.ZipFile(output / 'app.zip') as archive:
        assert archive.testzip() is None
        assert 'models/model.gguf' not in archive.namelist()
        assert archive.read('runtime/library.dll') == contents['runtime/library.dll']
        assert archive.getinfo('runtime/library.dll').compress_type == zipfile.ZIP_DEFLATED
        assert archive.getinfo('runtime/library.dll').compress_size < len(contents['runtime/library.dll']) / 10
        manifest = json.loads(archive.read('package-manifest.json'))
        assert 'licenses/notice.txt' in {f['path'] for f in manifest['files']}
    assert (output / 'model.gguf').read_bytes() == contents['models/model.gguf']
    with zipfile.ZipFile(output / 'NPCChatSetup-offline.zip') as archive:
        assert archive.testzip() is None
        assert archive.getinfo('payloads/app.zip').compress_type == zipfile.ZIP_STORED
        assert archive.getinfo('payloads/model.gguf').compress_type == zipfile.ZIP_STORED
        assert archive.read('payloads/app.zip') == (output / 'app.zip').read_bytes()
    release = json.loads((output / 'release.json').read_text())
    for payload in release['payloads']:
        data = (output / payload['name']).read_bytes()
        assert payload['sha256'] == hashlib.sha256(data).hexdigest()
        assert payload['bytes'] == len(data)
