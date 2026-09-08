import asyncio

import httpx
import pytest

from app.services import health_service


def test_hanging_dependencies_are_cancelled_concurrently():
    started = set()
    cancelled = set()

    async def run():
        both_started = asyncio.Event()

        async def hang(name):
            started.add(name)
            if len(started) == 2:
                both_started.set()
            try:
                await both_started.wait()
                await asyncio.Event().wait()
            finally:
                cancelled.add(name)

        return await health_service.check_dependencies(
            {name: lambda name=name: hang(name) for name in ("llm", "redis")}, timeout_sec=0.1
        )

    result = asyncio.run(asyncio.wait_for(run(), timeout=2))
    assert result == {"llm": "timeout", "redis": "timeout"}
    assert started == cancelled == {"llm", "redis"}


@pytest.mark.parametrize("status,payload,valid", [
    (200, {"data": [{"id": "local-model"}]}, True),
    (200, {"data": []}, False),
    (200, {"data": [None]}, False),
    (200, {"data": [{"id": ""}]}, False),
    (200, {"status": "ok"}, False),
    (200, [], False),
    (503, {"error": "loading"}, False),
])
def test_real_llm_probe_uses_models_endpoint(monkeypatch, status, payload, valid):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, json=payload)

    client_class = httpx.AsyncClient
    monkeypatch.setattr(health_service.httpx, "AsyncClient", lambda **kwargs: client_class(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    if valid:
        asyncio.run(health_service.check_llm())
    else:
        with pytest.raises((ValueError, httpx.HTTPStatusError)):
            asyncio.run(health_service.check_llm())
    assert len(requests) == 1
    assert str(requests[0].url) == "http://127.0.0.1:8001/v1/models"
    assert requests[0].method == "GET"


def test_malformed_json_is_unavailable(monkeypatch):
    client_class = httpx.AsyncClient

    def handler(request):
        return httpx.Response(200, content=b"not JSON")

    monkeypatch.setattr(health_service.httpx, "AsyncClient", lambda **kwargs: client_class(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    assert asyncio.run(health_service.check_dependencies(
        {"llm": health_service.check_llm}, timeout_sec=1
    )) == {"llm": "unavailable"}


@pytest.mark.parametrize("error,expected", [
    (httpx.ConnectError("private address"), "unavailable"),
    (httpx.ReadTimeout("private address"), "timeout"),
])
def test_transport_errors_are_sanitized(error, expected):
    async def failed_probe():
        raise error

    assert asyncio.run(health_service.check_dependencies(
        {"llm": failed_probe}, timeout_sec=1
    )) == {"llm": expected}


@pytest.mark.parametrize("value,expected", [(-1, 0.1), (0, 0.1), (2, 2), (999, 10)])
def test_timeout_cannot_be_disabled_or_unbounded(value, expected):
    assert health_service.bounded_timeout(value) == expected
