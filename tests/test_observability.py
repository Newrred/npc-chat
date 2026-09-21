from dataclasses import replace
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.character_config import load_character_config
from app.config import Settings
from app.main import create_app
from app.observability import JsonlMetricsSink, TurnMetrics, runtime_manifest
from app.remote_access import RemoteConfig
from app.services.decision_service import LLMTransportError
from scripts.summarize_metrics import summarize
from tests.fakes import FakeLLM, FakeStore


class CaptureSink:
    def __init__(self):
        self.records = []
        self.closed = False

    def emit(self, record):
        self.records.append(record)

    def close(self):
        self.closed = True


def nested_keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(*(nested_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(nested_keys(item) for item in value), set())
    return set()


def test_runtime_manifest_allowlists_effective_non_secret_configuration():
    config = replace(Settings(), llm_api_key="PRIVATE_KEY", database_path="C:/private/database.sqlite3",
                     llm_base_url="http://private-host/v1", llm_model="safe-model")
    remote = SimpleNamespace(mode="guest", origin="https://private.example", guest_secret="PRIVATE_SECRET")
    manifest = runtime_manifest(config, remote,
        [load_character_config("default"), load_character_config("cartethyia")])
    rendered = json.dumps(manifest, ensure_ascii=False)
    assert manifest["llm_model"] == "safe-model" and manifest["generation_mode"] == config.llm_generation_mode
    assert set(manifest["characters"]) == {"default", "cartethyia"}
    assert "PRIVATE" not in rendered and "database.sqlite3" not in rendered and "private-host" not in rendered
    assert "origin" not in rendered.lower() and "api_key" not in rendered.lower()


def test_rotating_jsonl_and_summary_contain_no_conversation_content(tmp_path):
    path = tmp_path / "requests.jsonl"
    sink = JsonlMetricsSink(path, max_bytes=250, backup_count=2)
    for number in range(8):
        sink.emit({"event": "turn_complete", "outcome": "success", "total_ms": number + 1,
                   "queue_wait_ms": number, "character_id": "default"})
    sink.close()
    files = list(tmp_path.glob("requests.jsonl*"))
    assert 1 <= len(files) <= 3
    rows = []
    for file in files:
        rows.extend(json.loads(line) for line in file.read_text(encoding="utf-8").splitlines())
    result = summarize(rows)
    assert result["turns"] and result["outcomes"] == {"success": result["turns"]}
    assert not {"message", "reply", "user_id", "session_id", "profile_id", "turn_id"} & nested_keys(rows)


def test_api_records_success_replay_and_failure_without_raw_content():
    store, llm, sink = FakeStore(), FakeLLM(), CaptureSink()
    try:
        with TestClient(create_app(repository=store, llm_service=llm, metrics_sink=sink,
                                   remote_config=RemoteConfig(mode="local"))) as client:
            identity = client.post("/api/session", json={}).json()
            body = {**identity, "client_turn_id": "metric-turn", "message": "PRIVATE_CHAT_SENTINEL"}
            assert client.post("/api/chat", json=body).status_code == 200
            assert client.post("/api/chat", json=body).status_code == 200
            llm.error = LLMTransportError("PRIVATE_PROVIDER_SENTINEL")
            failed = {**identity, "client_turn_id": "metric-failure", "message": "PRIVATE_FAILURE_SENTINEL"}
            assert client.post("/api/chat", json=failed).status_code == 503
        turns = [row for row in sink.records if row["event"] == "turn_complete"]
        assert len(turns) == 3 and turns[0]["outcome"] == "success"
        assert turns[1]["outcome"] == "success" and turns[1]["replayed"]
        assert turns[2]["outcome"] == "failed" and turns[2]["error_code"] == "LLM_UNAVAILABLE"
        assert all(row["total_ms"] >= 0 and row["queue_wait_ms"] >= 0 for row in turns)
        rendered = json.dumps(sink.records, ensure_ascii=False)
        assert "PRIVATE_CHAT_SENTINEL" not in rendered
        assert "PRIVATE_FAILURE_SENTINEL" not in rendered
        assert "PRIVATE_PROVIDER_SENTINEL" not in rendered
        assert not {"message", "reply", "user_id", "session_id", "profile_id", "turn_id"} & nested_keys(sink.records)
        assert sink.closed
    finally:
        if not store.closed:
            store.engine.dispose()
            store.temporary.cleanup()


def test_cancelled_turn_metric_has_one_terminal_record_without_content():
    metric = TurnMetrics("default")
    metric.queue_started(3.25, 2)
    record = metric.finish("cancelled", "CLIENT_CANCELLED")
    assert record["outcome"] == "cancelled" and record["error_code"] == "CLIENT_CANCELLED"
    assert record["queue_wait_ms"] == 3.25 and record["queue_depth"] == 2
    assert metric.finish("success") is None
    assert not {"message", "reply", "user_id", "session_id", "profile_id", "turn_id"} & nested_keys(record)
