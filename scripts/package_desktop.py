"""Build a fresh internal portable folder; never copy developer config/data."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PYTHON_SHA256 = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_files(root):
    # Explicit product trees/extensions; no blanket repository copy.
    files = list((root / "app").rglob("*.py"))
    files += list((root / "app/characters").glob("*.json"))
    files += list((root / "migrations").rglob("*.py"))
    files += [root / "frontend" / name for name in ("index.html", "app.js", "styles.css", "config.js")]
    files += list((root / "frontend/faces").glob("*.png"))
    files += list((root / "frontend/characters").glob("*/faces/*.png"))
    files += [root / "scripts" / name for name in
              ("desktop_runtime.py", "desktop_server.py", "desktop_config.py", "local_runtime.py", "verify_desktop_package.py")]
    # Synthetic smoke fixture only; no test logs or personal traces.
    files += [root / "tests/__init__.py", root / "tests/fakes.py"]
    return sorted(set(p for p in files if p.is_file() and "__pycache__" not in p.parts))


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_manifest(output):
    def record(path):
        return {"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
    files = sorted(p for p in output.rglob("*") if p.is_file() and p.name != "package-manifest.json")
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(record, files))
    (output / "package-manifest.json").write_text(json.dumps({
        "format": 1, "distribution": "internal-test-only", "files": records,
    }, indent=2), encoding="utf-8")
    return records


def build(args):
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Output already exists; choose a new folder")
    for path in (args.python_zip, args.model, args.llama / "llama-server.exe",
                 args.webview / "msedgewebview2.exe", args.publish / "NpcChat.Desktop.exe"):
        if not path.is_file():
            raise ValueError(f"Missing build input: {path.name}")
    if digest(args.python_zip) != PYTHON_SHA256:
        raise ValueError("Python archive checksum mismatch")
    output.mkdir(parents=True)
    for source in source_files(ROOT):
        copy(source, output / source.relative_to(ROOT))
    shutil.copytree(args.publish, output, dirs_exist_ok=True)
    python = output / "runtime/python"
    python.mkdir(parents=True)
    with zipfile.ZipFile(args.python_zip) as archive:
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in archive.namelist()):
            raise ValueError("Unsafe archive path")
        archive.extractall(python)
    # Isolated sys.path: do not load user site, registry Python or arbitrary .pth files.
    (python / "python312._pth").write_text("python312.zip\n.\nLib\\site-packages\n..\\..\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                    "--only-binary=:all:", "--no-deps", "--target", str(python / "Lib/site-packages"),
                    "-r", str(ROOT / "desktop/requirements-runtime.lock")], check=True)
    for source in args.llama.iterdir():
        if source.is_file() and (source.suffix.lower() == ".dll" or source.name == "llama-server.exe"
                                 or source.name.startswith("LICENSE")):
            copy(source, output / "runtime/llama" / source.name)
    shutil.copytree(args.webview, output / "runtime/webview2")
    copy(args.model, output / "models/model.gguf")
    config = {"version": 1, "model": "models/model.gguf", "server": "runtime/llama/llama-server.exe",
              "settings": json.loads((ROOT / "desktop/portable-settings.json").read_text())}
    (output / "desktop-package.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    for name in ("requirements-runtime.lock", "portable-settings.json"):
        copy(ROOT / "desktop" / name, output / "build-info" / name)
    copy(ROOT / "docs/PORTABLE_DESKTOP.md", output / "READ-ME.md")
    # File integrity records, no machine paths or developer environment values.
    records = write_manifest(output)
    print(json.dumps({"files": len(records), "bytes": sum(p["bytes"] for p in records)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("output", "python-zip", "model", "llama", "webview", "publish"):
        parser.add_argument("--" + name, type=Path, required=True)
    build(parser.parse_args())
