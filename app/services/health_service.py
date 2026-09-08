import asyncio
from collections.abc import Awaitable, Callable

import httpx
from pydantic import BaseModel, Field

from app.config import settings


class AvailableModel(BaseModel):
    id: str = Field(min_length=1)


class ModelListing(BaseModel):
    data: list[AvailableModel] = Field(min_length=1)


async def check_llm() -> None:
    """Probe model availability without generating or logging conversation text."""
    async with httpx.AsyncClient(timeout=bounded_timeout(settings.health_timeout_sec)) as client:
        response = await client.get(
            f"{settings.llm_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )
        response.raise_for_status()
        ModelListing.model_validate(response.json())


def bounded_timeout(timeout_sec: float) -> float:
    return max(0.1, min(timeout_sec, 10.0))


async def check_dependencies(
    checks: dict[str, Callable[[], Awaitable[None]]], *, timeout_sec: float
) -> dict[str, str]:
    async def probe(check: Callable[[], Awaitable[None]]) -> str:
        try:
            await asyncio.wait_for(check(), timeout=bounded_timeout(timeout_sec))
        except (TimeoutError, httpx.TimeoutException):
            return "timeout"
        except Exception:
            # Do not expose connection URLs, credentials, or exception bodies.
            return "unavailable"
        return "ok"

    results = await asyncio.gather(*(probe(check) for check in checks.values()))
    return dict(zip(checks, results))
