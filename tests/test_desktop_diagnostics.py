import subprocess

import pytest

from scripts.desktop_diagnostics import error_code


@pytest.mark.parametrize("exc,stage,expected", [
    (RuntimeError("Port 8003 is occupied; its process will not be stopped."), "ports", "PORT_BUSY"),
    (RuntimeError("Need at least 2048 MiB free VRAM before loading."), "model_check", "LOW_VRAM"),
    (RuntimeError("GGUF missing; path/private"), "model_check", "MODEL_MISSING"),
    (RuntimeError("llama-server executable missing; path/private"), "model_check", "ENGINE_MISSING"),
    (RuntimeError("Installed llama.cpp lacks required flags"), "model_check", "ENGINE_INCOMPATIBLE"),
    (RuntimeError("Another launcher is running."), "configuration", "ALREADY_STARTING"),
    (ValueError("private config"), "configuration", "PACKAGE_INVALID"),
    (subprocess.CalledProcessError(255, "secret command"), "model_check", "GPU_OR_ENGINE_CHECK_FAILED"),
    (FileNotFoundError("private path"), "model_check", "GPU_OR_ENGINE_CHECK_FAILED"),
    (PermissionError("private path"), "server_loading", "ACCESS_DENIED"),
    (PermissionError("private path"), "configuration", "ACCESS_DENIED"),
    (RuntimeError("START_TIMEOUT"), "model_loading", "START_TIMEOUT"),
    (RuntimeError("START_CANCELLED"), "model_loading", "START_CANCELLED"),
    (RuntimeError("PROCESS_EXITED"), "ready", "PROCESS_EXITED"),
    (RuntimeError("token=secret, user conversation"), "ready", "START_FAILED"),
    (OSError("private path and username"), "ready", "START_FAILED"),
])
def test_errors_only_emit_known_codes(exc, stage, expected):
    assert error_code(exc, stage) == expected


def test_progress_protocol_is_separate_from_stdout_logs(capsys):
    import json
    from scripts.desktop_runtime import progress
    progress("ports")
    assert json.loads(capsys.readouterr().out) == {"desktop": "progress", "stage": "ports"}


def test_parent_pipe_closed_does_not_skip_model_cleanup():
    from scripts.desktop_runtime import stop_services
    names = []

    class Runtime:
        def stop(self, name, *, quiet=False):
            assert quiet
            names.append(name)

    stop_services(Runtime())
    assert names == ["web", "llm"]
