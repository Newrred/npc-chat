"""Read-only package integrity verification; not a digital signature."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != 1:
        raise ValueError("Unsupported manifest")

    def check(item):
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return item["path"]
        if path.stat().st_size != item["bytes"]:
            return item["path"]
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != item["sha256"]:
                return item["path"]
        return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        return [name for name in pool.map(check, manifest["files"]) if name]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    errors = verify(parser.parse_args().root)
    print(json.dumps({"valid": not errors, "changed_or_missing": errors}))
    raise SystemExit(bool(errors))
