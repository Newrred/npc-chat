"""Build internal download/offline installers from a verified portable package."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from urllib.parse import urlsplit
import re

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.package_notices import collect, enforce_distribution
from scripts.verify_desktop_package import verify

ROOT = Path(__file__).resolve().parents[1]


def download_url(url):
    """Normalize public Drive share URLs; never persist temporary query tokens."""
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Use stable public HTTPS payload URLs without credentials or query tokens')
    if parsed.netloc == 'drive.google.com':
        match = re.fullmatch(r'/file/d/([A-Za-z0-9_-]+)/view', parsed.path)
        if match and parsed.query in ('', 'usp=sharing', 'usp=drive_link'):
            return 'https://drive.usercontent.google.com/download?id=' + match[1] + '&export=download&confirm=t'
    if parsed.query:
        raise ValueError('Use stable public HTTPS payload URLs without credentials or query tokens')
    return url


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build(args):
    enforce_distribution(args.distribution)
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Choose a new output folder')
    if bool(args.app_url) != bool(args.model_url):
        raise ValueError('Both HTTPS payload URLs are required for a download installer')
    app_url = download_url(args.app_url) if args.app_url else None
    model_url = download_url(args.model_url) if args.model_url else None
    package = args.package.resolve()
    errors = verify(package)
    if errors:
        raise ValueError('Portable package integrity failed')
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,63}', args.release_id) or '..' in args.release_id:
        raise ValueError('Invalid release ID')
    manifest = json.loads((package / 'package-manifest.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True)
    report = collect(package, output / 'notices', ROOT / 'desktop/requirements-runtime.lock')
    mapping = {}
    for f in manifest['files']:
        path = (package / f['path']).resolve()
        if not path.is_relative_to(package):
            raise ValueError('Unsafe manifest path')
        mapping[f['path']] = path
    for p in (output / 'notices').rglob('*'):
        if p.is_file():
            mapping['licenses/' + p.relative_to(output / 'notices').as_posix()] = p
    records = []
    old = {f['path']: f for f in manifest['files']}
    for name, path in sorted(mapping.items()):
        records.append(old[name] if name in old and path.is_relative_to(package) else
                       {'path': name, 'bytes': path.stat().st_size, 'sha256': digest(path)})
    manifest_path = output / 'package-manifest.json'
    manifest_path.write_text(json.dumps({'format': 1, 'distribution': 'internal-test-only', 'files': records}, indent=2), encoding='utf-8')
    model = mapping.pop('models/model.gguf')
    mapping['package-manifest.json'] = manifest_path
    app_zip = output / 'app.zip'
    # DLLs and source compress well. Deflate is supported by the Windows installer.
    # Model bytes remain unchanged; avoid a second compression pass over app.zip.
    with zipfile.ZipFile(app_zip, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for name, path in sorted(mapping.items()):
            archive.write(path, name)
    model_target = output / 'model.gguf'
    shutil.copyfile(model, model_target)
    payloads = [{'name': name, 'bytes': path.stat().st_size, 'sha256': digest(path), 'url': url}
                for name, path, url in [('app.zip', app_zip, app_url), ('model.gguf', model_target, model_url)]]
    release = {'format': 1, 'id': args.release_id, 'expandedBytes': sum(p.stat().st_size for p in mapping.values()),
               'distribution': 'internal-test-only', 'manifestSha256': digest(manifest_path), 'payloads': payloads}
    config = output / 'release.json'
    config.write_text(json.dumps(release, indent=2), encoding='utf-8')
    dotnet = ROOT / '.runtime/dotnet/dotnet.exe'
    subprocess.run([str(dotnet) if dotnet.exists() else 'dotnet', 'publish', str(ROOT / 'desktop/NpcChat.Setup/NpcChat.Setup.csproj'),
                    '-c', 'Release', '-r', 'win-x64', '--self-contained', 'true', '-o', str(output / 'bootstrap'),
                    '-p:InstallerManifestPath=' + str(config)], check=True)
    base = output / 'bootstrap/NpcChat.Setup.exe'
    # Windows rejected the measured 7.9GB EXE overlay. Use ZIP64 for offline transport.
    offline = output / 'NPCChatSetup-offline.zip'
    with zipfile.ZipFile(offline, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        archive.write(base, 'NPCChatSetup.exe', compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
        for p in payloads:
            archive.write(output / p['name'], 'payloads/' + p['name'])
    if args.app_url:
        shutil.copyfile(base, output / 'NPCChatSetup-online.exe')
    summary = {'release': args.release_id, 'offline_bytes': offline.stat().st_size,
               'offline_sha256': digest(offline), 'online_created': bool(args.app_url),
               'notices': len(report['notices']), 'release_allowed': False}
    (output / 'build-result.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--release-id', required=True)
    p.add_argument('--app-url')
    p.add_argument('--model-url')
    p.add_argument('--distribution', choices=['internal', 'release'], default='internal')
    build(p.parse_args())
