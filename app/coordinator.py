"""One inference at a time, finite waiting queue, cancellation without partial commits."""
import asyncio
from dataclasses import dataclass

from app.errors import ChatError


@dataclass
class Job:
    function: object
    future: asyncio.Future
    started: asyncio.Event
    cancelled: bool = False


class TurnCoordinator:
    def __init__(self, capacity=8, wait_seconds=30):
        if not 1 <= capacity <= 100 or not 0 < wait_seconds <= 600:
            raise ValueError("Invalid queue limits")
        self.queue = asyncio.Queue(maxsize=capacity)
        self.wait_seconds = wait_seconds
        self.worker = None
        self.closing = False
        self.active = None

    async def submit(self, function):
        if self.closing:
            raise ChatError("SHUTTING_DOWN", "서버가 종료 중입니다.", 503, True)
        if self.worker is None:
            self.worker = asyncio.create_task(self._run())
        future = asyncio.get_running_loop().create_future()
        # Retrieve exceptions even if the HTTP caller disconnects.
        future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        job = Job(function, future, asyncio.Event())
        try:
            self.queue.put_nowait(job)
        except asyncio.QueueFull:
            raise ChatError("QUEUE_FULL", "대기 중인 대화가 많습니다. 잠시 후 다시 시도해 주세요.", 429, True) from None
        try:
            try:
                await asyncio.wait_for(job.started.wait(), self.wait_seconds)
            except TimeoutError:
                job.cancelled = True
                raise ChatError("QUEUE_TIMEOUT", "대화 대기 시간이 초과됐습니다.", 503, True) from None
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            job.cancelled = True
            raise

    async def _run(self):
        while True:
            job = await self.queue.get()
            try:
                if job is None:
                    return
                job.started.set()
                if job.cancelled:
                    job.future.cancel()
                    continue
                self.active = job
                try:
                    value = await job.function(lambda: job.cancelled)
                    if not job.future.done():
                        job.future.set_result(value)
                except Exception as exc:
                    if not job.future.done():
                        job.future.set_exception(exc)
                finally:
                    self.active = None
            finally:
                self.queue.task_done()

    async def close(self):
        self.closing = True
        if self.active:
            self.active.cancelled = True
        if self.worker and not self.worker.done():
            while not self.queue.empty():
                job = self.queue.get_nowait()
                job.cancelled = True
                job.started.set()
                job.future.cancel()
                self.queue.task_done()
            await self.queue.put(None)
            await self.worker
