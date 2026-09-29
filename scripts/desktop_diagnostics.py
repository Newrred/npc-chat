"""Allowlisted supervisor protocol: never emit arbitrary exception text."""
import subprocess

STAGES = {"configuration", "ports", "model_check", "model_loading", "server_loading", "ready"}


def error_code(exc, stage):
    if isinstance(exc, RuntimeError):
        message = str(exc)
        if message in {"START_CANCELLED", "PROCESS_EXITED", "START_TIMEOUT", "MISSING_DESKTOP_TOKEN"}:
            return message
        if message.startswith("Port ") and "occupied" in message:
            return "PORT_BUSY"
        if message.startswith("Need at least "):
            return "LOW_VRAM"
        if message.startswith("GGUF missing"):
            return "MODEL_MISSING"
        if message.startswith("llama-server executable missing"):
            return "ENGINE_MISSING"
        if message.startswith("Installed llama.cpp lacks"):
            return "ENGINE_INCOMPATIBLE"
        if message.startswith("Another launcher"):
            return "ALREADY_STARTING"
    if isinstance(exc, PermissionError):
        return "ACCESS_DENIED"
    if stage == "configuration" and isinstance(exc, (ValueError, KeyError, TypeError, OSError)):
        return "PACKAGE_INVALID"
    if stage == "model_check" and isinstance(exc, (FileNotFoundError, subprocess.CalledProcessError)):
        return "GPU_OR_ENGINE_CHECK_FAILED"
    return "START_FAILED"
