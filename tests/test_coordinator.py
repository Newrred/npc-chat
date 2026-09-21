import asyncio

import pytest

from app.coordinator import TurnCoordinator
from app.errors import ChatError


def test_single_active_queue_full_cancellation_and_cleanup():
    async def run():
        gate = TurnCoordinator(capacity=1, wait_seconds=1)
        started, release = asyncio.Event(), asyncio.Event()
        committed = []
        async def first(cancelled):
            started.set()
            await release.wait()
            if not cancelled():
                committed.append("first")
        async def second(cancelled):
            if not cancelled():
                committed.append("second")
        active = asyncio.create_task(gate.submit(first))
        await started.wait()
        waiting = asyncio.create_task(gate.submit(second))
        await asyncio.sleep(0)
        with pytest.raises(ChatError) as exc:
            await gate.submit(second)
        assert exc.value.code == "QUEUE_FULL"
        active.cancel()
        done, _ = await asyncio.wait([active], timeout=1)
        if not done:
            release.set()
        assert done, "Cancellation must finish even when the start event completes concurrently"
        with pytest.raises(asyncio.CancelledError):
            await active
        assert not committed
        release.set()
        await waiting
        await gate.close()
        assert committed == ["second"]
        assert gate.active is None and gate.queue.empty()
    asyncio.run(run())


def test_queue_timeout_does_not_run_later():
    async def run():
        gate = TurnCoordinator(capacity=2, wait_seconds=.03)
        started, release = asyncio.Event(), asyncio.Event()
        ran = []
        async def first(cancelled):
            started.set()
            await release.wait()
        async def late(cancelled):
            ran.append(True)
        active = asyncio.create_task(gate.submit(first))
        await started.wait()
        with pytest.raises(ChatError) as exc:
            await gate.submit(late)
        assert exc.value.code == "QUEUE_TIMEOUT"
        release.set()
        await active
        await gate.close()
        assert ran == []
    asyncio.run(run())


def test_queue_start_observer_receives_wait_and_depth():
    async def run():
        gate = TurnCoordinator(capacity=2, wait_seconds=1)
        started, release = asyncio.Event(), asyncio.Event()
        observed = []
        async def first(_cancelled):
            started.set()
            await release.wait()
        async def second(_cancelled):
            return "ok"
        active = asyncio.create_task(gate.submit(first))
        await started.wait()
        waiting = asyncio.create_task(gate.submit(
            second, on_start=lambda wait_ms, depth: observed.append((wait_ms, depth))))
        await asyncio.sleep(0)
        release.set()
        assert await waiting == "ok"
        await active
        await gate.close()
        assert len(observed) == 1 and observed[0][0] >= 0 and observed[0][1] == 1
    asyncio.run(run())
