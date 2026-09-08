from argparse import Namespace
import os
import socket
import subprocess
import sys

import pytest

from scripts import local_runtime as runtime


def args(**updates):
    values = dict(action="start-llm", executable="missing-executable", model="", alias="local-model",
                  min_free_mib=2048, context=2048, gpu_layers="12", timeout=1, max_tokens=256, reuse_llm=False)
    return Namespace(**(values | updates))


def test_missing_paths_fail_before_gpu(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "gpu_info", lambda: pytest.fail("must validate paths first"))
    with pytest.raises(RuntimeError, match="executable missing"):
        runtime.model_command(args())
    with pytest.raises(RuntimeError, match="GGUF missing"):
        runtime.model_command(args(executable=sys.executable))


def test_gpu_guard_and_effective_command(monkeypatch, tmp_path):
    model = tmp_path / "model.gguf"
    model.touch()
    monkeypatch.setattr(runtime, "gpu_info", lambda: {"free_mib": 1024})
    with pytest.raises(RuntimeError, match="VRAM"):
        runtime.model_command(args(executable=sys.executable, model=str(model)))
    monkeypatch.setattr(runtime, "gpu_info", lambda: {"free_mib": 4096})
    monkeypatch.setattr(runtime.subprocess, "run", lambda *a, **k: Namespace(
        stdout="--fit --fit-target --reasoning-budget --log-disable"))
    command = runtime.model_command(args(executable=sys.executable, model=str(model)))
    assert command[command.index("--ctx-size") + 1] == "2048"
    assert command[command.index("--parallel") + 1] == "1"
    assert command[command.index("--reasoning-budget") + 1] == "0"


def test_port_collision_preserves_listener():
    with socket.socket() as listener:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(RuntimeError, match="occupied"):
            runtime.free_port(listener.getsockname()[1])
        assert listener.fileno() >= 0


def test_actual_process_identity_and_repeat_stop(tmp_path):
    manager = runtime.Runtime(tmp_path)
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                 creationflags=runtime.HIDDEN)
    try:
        with manager.locked():
            record = manager.launch("llm", [sys.executable, "-c", "import time; time.sleep(60)"], os.environ)
            assert runtime.matches(record)
            wrong = dict(runtime.identity(unrelated.pid), created=0)
            runtime.stop_owned(wrong)
            assert unrelated.poll() is None
            manager.stop("llm")
            manager.stop("llm")
            assert not runtime.matches(record)
            assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_readiness_timeout_and_early_exit(monkeypatch):
    monkeypatch.setattr(runtime, "matches", lambda _: True)
    monkeypatch.setattr(runtime, "ready", lambda *a: False)
    with pytest.raises(RuntimeError, match="timed out"):
        runtime.wait_ready({}, "http://fake", 0.01)
    monkeypatch.setattr(runtime, "matches", lambda _: False)
    with pytest.raises(RuntimeError, match="exited"):
        runtime.wait_ready({}, "http://fake", 1)


@pytest.mark.parametrize("failure", [False, True])
def test_start_llm_success_rollback_and_repeat(monkeypatch, tmp_path, failure):
    manager = runtime.Runtime(tmp_path)
    monkeypatch.setattr(runtime, "free_port", lambda _: None)
    monkeypatch.setattr(runtime, "model_command", lambda _: [sys.executable, "-c", "import time; time.sleep(60)"])
    def wait(*a):
        if failure:
            raise RuntimeError("injected readiness failure")
    monkeypatch.setattr(runtime, "wait_ready", wait)
    monkeypatch.setattr(runtime, "ready", lambda *a: True)
    with manager.locked():
        try:
            if failure:
                with pytest.raises(RuntimeError):
                    manager.start(args())
                assert manager.state == {}
            else:
                manager.start(args())
                first = manager.state["llm"]
                manager.start(args())
                assert manager.state["llm"] == first
        finally:
            manager.stop("llm")


def test_shared_model_not_adopted(monkeypatch, tmp_path):
    manager = runtime.Runtime(tmp_path)
    monkeypatch.setattr(runtime, "ready", lambda *a: True)
    monkeypatch.setattr(manager, "launch", lambda *a: pytest.fail("shared model must not be launched"))
    with manager.locked():
        manager.start(args(reuse_llm=True))
        assert manager.state == {}
        manager.stop("llm")


@pytest.mark.parametrize("shared_model", [False, True])
def test_partial_web_failure_preserves_preexisting_model_and_redis(monkeypatch, tmp_path, shared_model):
    import redis
    monkeypatch.setattr(runtime, "prepare_database", lambda: None)
    class RedisProbe:
        def ping(self):
            return True

        def close(self):
            pass

    monkeypatch.setattr(redis.Redis, "from_url", lambda *a, **k: RedisProbe())
    monkeypatch.setattr(runtime, "free_port", lambda _: None)
    monkeypatch.setattr(runtime, "ready", lambda *a: True)
    command = [sys.executable, "-c", "import time; time.sleep(60)"]
    monkeypatch.setattr(runtime, "model_command", lambda _: command)
    manager = runtime.Runtime(tmp_path)
    real_launch = manager.launch
    monkeypatch.setattr(manager, "launch", lambda name, _command, env: real_launch(name, command, env))
    def wait(record, url, *a):
        if ":8000/" in url:
            raise RuntimeError("web startup failed")
    monkeypatch.setattr(runtime, "wait_ready", wait)
    with manager.locked():
        existing = real_launch("llm", command, os.environ) if shared_model else None
        try:
            with pytest.raises(RuntimeError, match="web startup"):
                manager.start(args(action="start-local"))
            assert "web" not in manager.state
            if shared_model:
                assert runtime.matches(existing)
                assert manager.state["llm"] == existing
            else:
                assert manager.state == {}
        finally:
            manager.stop("llm")


def test_missing_database_fails_before_any_launch(monkeypatch, tmp_path):
    def missing():
        raise RuntimeError("SQLite unavailable")
    monkeypatch.setattr(runtime, "prepare_database", missing)
    monkeypatch.setattr(runtime, "free_port", lambda _: None)
    manager = runtime.Runtime(tmp_path)
    monkeypatch.setattr(manager, "launch", lambda *a: pytest.fail("must not launch without database"))
    with manager.locked(), pytest.raises(RuntimeError, match="SQLite unavailable"):
        manager.start(args(action="start-local"))


def test_full_lifecycle_success_and_duplicate_start(monkeypatch, tmp_path):
    import redis
    monkeypatch.setattr(runtime, "prepare_database", lambda: None)
    class RedisProbe:
        def ping(self):
            return True

        def close(self):
            pass
    monkeypatch.setattr(redis.Redis, "from_url", lambda *a, **k: RedisProbe())
    monkeypatch.setattr(runtime, "free_port", lambda _: None)
    monkeypatch.setattr(runtime, "ready", lambda *a: True)
    monkeypatch.setattr(runtime, "wait_ready", lambda *a: None)
    command = [sys.executable, "-c", "import time; time.sleep(60)"]
    monkeypatch.setattr(runtime, "model_command", lambda _: command)
    manager = runtime.Runtime(tmp_path)
    real_launch = manager.launch
    monkeypatch.setattr(manager, "launch", lambda name, _command, env: real_launch(name, command, env))
    with manager.locked():
        try:
            manager.start(args(action="start-local"))
            original = dict(manager.state)
            assert set(original) == {"llm", "web"}
            manager.start(args(action="start-local"))
            assert manager.state == original
        finally:
            manager.stop("web")
            manager.stop("llm")
        assert all(not runtime.matches(record) for record in original.values())


def test_benchmark_summary_distinguishes_retry_recovery_and_failure():
    from scripts.benchmark_local import summarize
    result = summarize([
        {"success": True, "attempts": 1, "elapsed_sec": 1},
        {"success": True, "attempts": 2, "elapsed_sec": 2},
        {"success": False, "elapsed_sec": 3},
    ])
    assert result["first_pass_rate"] == 1 / 3
    assert result["final_schema_rate"] == 2 / 3
    assert result["retry_recoveries"] == 1
