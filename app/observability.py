"""Private-content-free runtime and turn metrics for local operations."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
import uuid


METRICS_SCHEMA_VERSION = 1
RETRIEVER_VERSION = "active-topic-v2"
PROMPT_INPUT_VERSION = "token-budget-v2"


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def prompt_fingerprint(character):
    payload = "\0".join((character.character_id, character.system_prompt,
                         character.dialogue_prompt or "", character.grounded_recall_template))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def runtime_manifest(config, remote_config, characters):
    """Return only allow-listed non-secret effective settings."""
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "event": "runtime_manifest",
        "recorded_at": _utc_now(),
        "app_version": "0.5.0",
        "access_mode": remote_config.mode,
        "generation_mode": config.llm_generation_mode,
        "metadata_context_mode": config.metadata_context_mode,
        "llm_backend": config.llm_backend,
        "llm_model": config.llm_model,
        "json_mode": config.llm_json_mode,
        "output_contract": config.llm_output_contract,
        "context_tokens": config.llm_context,
        "max_output_tokens": config.llm_max_tokens,
        "token_count_mode": config.token_count_mode,
        "temperature": config.llm_temperature,
        "top_p": config.llm_top_p,
        "top_k": config.llm_top_k,
        "presence_penalty": config.llm_presence_penalty,
        "frequency_penalty": config.llm_frequency_penalty,
        "repetition_penalty": config.llm_repetition_penalty,
        "queue_capacity": config.queue_capacity,
        "queue_wait_sec": config.queue_wait_sec,
        "comfy_enabled": config.comfy_enabled,
        "debug_trace": config.debug_trace,
        "retriever_version": RETRIEVER_VERSION,
        "prompt_input_version": PROMPT_INPUT_VERSION,
        "characters": {item.character_id: prompt_fingerprint(item) for item in characters},
    }


class NoopMetricsSink:
    def emit(self, _record):
        pass

    def close(self):
        pass


class JsonlMetricsSink:
    def __init__(self, path, *, max_bytes=5_000_000, backup_count=3):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("npc.metrics." + hashlib.sha256(str(target).encode()).hexdigest()[:12])
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handler = RotatingFileHandler(target, maxBytes=max_bytes, backupCount=backup_count,
                                           encoding="utf-8")
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.handlers.clear()
        self.logger.addHandler(self.handler)

    def emit(self, record):
        self.logger.info(json.dumps(record, ensure_ascii=False, separators=(",", ":")))

    def close(self):
        self.handler.flush()
        self.handler.close()
        self.logger.handlers.clear()


def create_metrics_sink(config):
    if not config.metrics_enabled:
        return NoopMetricsSink()
    return JsonlMetricsSink(config.metrics_path, max_bytes=config.metrics_max_bytes,
                            backup_count=config.metrics_backup_count)


@dataclass
class TurnMetrics:
    character_id: str
    started: float = field(default_factory=time.monotonic)
    metric_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    values: dict = field(default_factory=dict)
    emitted: bool = False

    def elapsed(self, name, started):
        self.values[name] = round((time.monotonic() - started) * 1000, 3)

    def queue_started(self, wait_ms, depth):
        self.values["queue_wait_ms"] = round(wait_ms, 3)
        self.values["queue_depth"] = depth

    def observe_generation(self, generated):
        stages = tuple(getattr(generated, "stages", ()) or ())
        self.values["tokenizer_requests"] = getattr(generated, "tokenizer_requests", None)
        self.values["attempts"] = getattr(generated, "attempts", None)
        self.values["parse_failures"] = getattr(generated, "parse_failures", None)
        self.values["transport_failures"] = getattr(generated, "transport_failures", None)
        self.values["prompt_tokens"] = getattr(generated, "prompt_tokens", None)
        self.values["completion_tokens"] = getattr(generated, "completion_tokens", None)
        self.values["context_trimmed"] = getattr(generated, "context_trimmed", None)
        self.values["grounded_recall"] = getattr(generated, "grounded_recall", None)
        self._observe_stages(stages)

    def observe_failure(self, error):
        stages = tuple(getattr(error, "stages", ()) or ())
        self.values["tokenizer_requests"] = getattr(error, "tokenizer_requests", None)
        self.values["attempts"] = sum(stage.attempts for stage in stages)
        self.values["parse_failures"] = sum(stage.parse_failures for stage in stages)
        self.values["transport_failures"] = sum(stage.transport_failures for stage in stages)
        self.values["prompt_tokens"] = sum(stage.prompt_tokens for stage in stages)
        self.values["completion_tokens"] = sum(stage.completion_tokens for stage in stages)
        self.values["context_trimmed"] = any(stage.context_trimmed for stage in stages)
        self._observe_stages(stages)

    def _observe_stages(self, stages):
        safe_stages = []
        for stage in stages:
            safe_stages.append({
                "stage": stage.stage,
                "attempts": stage.attempts,
                "parse_failures": stage.parse_failures,
                "transport_failures": stage.transport_failures,
                "prompt_tokens": stage.prompt_tokens,
                "completion_tokens": stage.completion_tokens,
                "context_trimmed": stage.context_trimmed,
                "prepare_ms": round(stage.prepare_sec * 1000, 3),
                "infer_ms": round(stage.inference_sec * 1000, 3),
                "elapsed_ms": round(stage.elapsed_sec * 1000, 3),
                "provider": stage.provider_metrics,
            })
        self.values["llm_stages"] = safe_stages
        for prefix, predicate in (("reply", lambda name: name.startswith("reply")),
                                  ("metadata", lambda name: name == "metadata")):
            selected = [stage for stage in stages if predicate(stage.stage)]
            self.values[prefix + "_prepare_ms"] = round(sum(x.prepare_sec for x in selected) * 1000, 3)
            self.values[prefix + "_infer_ms"] = round(sum(x.inference_sec for x in selected) * 1000, 3)

    def finish(self, outcome, error_code=None):
        if self.emitted:
            return None
        self.emitted = True
        return {
            "schema_version": METRICS_SCHEMA_VERSION,
            "event": "turn_complete",
            "recorded_at": _utc_now(),
            "metric_id": self.metric_id,
            "character_id": self.character_id,
            "outcome": outcome,
            "error_code": error_code,
            "total_ms": round((time.monotonic() - self.started) * 1000, 3),
            **self.values,
        }
