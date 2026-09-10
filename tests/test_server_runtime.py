from contextlib import contextmanager

from dotenv import dotenv_values
import pytest

from scripts import server_runtime


def complete_config():
    return {
        "NPC_MODEL": "model",
        "NPC_API_KEY": "key",
        "LLAMA_MODEL_PATH": "model.gguf",
        "LLAMA_SERVER_PATH": "llama-server",
        "NPC_DATABASE_PATH": "chat.sqlite3",
        "NPC_GUEST_SECRET": "secret",
    }


def test_tunnel_origin_uses_latest_issued_url():
    text = "https://old-one.trycloudflare.com\nhttps://new-two.trycloudflare.com"
    assert server_runtime.tunnel_origin(text) == "https://new-two.trycloudflare.com"
    assert server_runtime.tunnel_origin("waiting") is None


def test_load_config_rejects_missing_and_incomplete_files(tmp_path):
    with pytest.raises(RuntimeError, match="missing"):
        server_runtime.load_config(tmp_path / "missing.env")
    path = tmp_path / "test.env"
    path.write_text("NPC_MODEL=model\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="incomplete"):
        server_runtime.load_config(path)


def test_write_config_round_trips_values_without_printing(tmp_path):
    path = tmp_path / "test.env"
    values = complete_config() | {"NPC_PUBLIC_ORIGIN": "https://example.test"}
    server_runtime.write_config(path, values)
    assert dict(dotenv_values(path, interpolate=False)) == values


def test_wait_http_fails_if_owned_process_exits(monkeypatch):
    monkeypatch.setattr(server_runtime, "matches", lambda _: False)
    with pytest.raises(RuntimeError, match="exited"):
        server_runtime.wait_http({}, "http://example.test", 1)


def test_status_reports_complete_stack_without_secrets(monkeypatch, capsys):
    values = complete_config()

    class FakeRuntime:
        state = {name: {"name": name} for name in ("llm", "web", "admin", "tunnel")}

        @contextmanager
        def locked(self):
            yield

    monkeypatch.setattr(server_runtime, "load_config", lambda _: (None, values))
    monkeypatch.setattr(server_runtime, "Runtime", FakeRuntime)
    monkeypatch.setattr(server_runtime, "matches", lambda record: bool(record))
    monkeypatch.setattr(server_runtime, "ready", lambda *args: True)
    monkeypatch.setattr(server_runtime, "http_ok", lambda *args, **kwargs: True)
    monkeypatch.setattr(server_runtime, "current_origin", lambda _: "https://public.example")

    assert server_runtime.status_stack("unused") == 0
    output = capsys.readouterr().out
    assert "https://public.example" in output
    assert values["NPC_GUEST_SECRET"] not in output
