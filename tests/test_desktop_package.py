import json

import pytest

from scripts.desktop_config import inside, load_package
from scripts.package_desktop import source_files, build


def test_package_config_relative_and_no_credentials(tmp_path):
    (tmp_path / "model.gguf").touch()
    (tmp_path / "server.exe").touch()
    config = {"version": 1, "model": "model.gguf", "server": "server.exe", "settings": {"LLAMA_CONTEXT": "4096"}}
    path = tmp_path / "desktop-package.json"
    path.write_text(json.dumps(config))
    env = load_package(tmp_path)
    assert env["LLAMA_MODEL_PATH"] == str(tmp_path / "model.gguf")
    assert env["PYTHON_DOTENV_DISABLED"] == "1"
    config["settings"]["NPC_API_KEY"] = "not-allowed"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="Unknown"):
        load_package(tmp_path)


@pytest.mark.parametrize("value", ["../outside.gguf", "missing.gguf", "", "x/../../outside"])
def test_package_rejects_escaping_or_missing_files(tmp_path, value):
    with pytest.raises(ValueError):
        inside(tmp_path, value)


def test_source_allowlist_does_not_ship_private_data(tmp_path):
    for name in [".env", ".runtime/chat.sqlite3", "app/__pycache__/secret.pyc", "app/static/generated/private.png",
                 "frontend/private.json", "tests/private_trace.json", "app/main.py", "frontend/faces/neutral.png"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    assert {p.relative_to(tmp_path).as_posix() for p in source_files(tmp_path)} == {
        "app/main.py", "frontend/faces/neutral.png"}


def test_builder_never_overwrites_existing_folder(tmp_path):
    from types import SimpleNamespace
    with pytest.raises(ValueError, match="already exists"):
        build(SimpleNamespace(output=tmp_path))


def test_manifest_detects_modified_and_missing_files(tmp_path):
    from scripts.package_desktop import write_manifest
    from scripts.verify_desktop_package import verify
    one, two = tmp_path / "one", tmp_path / "two"
    one.write_text("original")
    two.write_text("keep")
    write_manifest(tmp_path)
    assert verify(tmp_path) == []
    one.write_text("tampered")
    two.unlink()
    assert verify(tmp_path) == ["one", "two"]
