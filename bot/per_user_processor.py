import asyncio
import logging
from typing import Any, Awaitable, Dict

from telegram import Update
from telegram.ext import BaseUpdateProcessor

logger = logging.getLogger(__name__)


class PerUserUpdateProcessor(BaseUpdateProcessor):
    """Processes different users' updates concurrently, each user's strictly in order.

    Every user gets their own FIFO queue drained by a single worker task, so one user's
    slow step (Gemini, sending) never holds up anyone else, while their own taps can't
    overlap (no double sends, no racing conversation state).

    do_process_update only enqueues and returns, so a user who taps repeatedly fills their
    own queue rather than the shared concurrency slots. The overall cap is enforced inside
    the workers, and only while an update is actually running.
    """

    def __init__(self, max_concurrent_updates: int):
        super().__init__(max_concurrent_updates)
        self._running = asyncio.Semaphore(max_concurrent_updates)
        self._queues: Dict[Any, asyncio.Queue] = {}
        self._workers: Dict[Any, asyncio.Task] = {}

    @staticmethod
    def _key(update: object) -> Any:
        if isinstance(update, Update):
            if update.effective_user:
                return update.effective_user.id
            if update.effective_chat:
                return ("chat", update.effective_chat.id)
        return None

    async def do_process_update(self, update: object, coroutine: Awaitable[Any]) -> None:
        key = self._key(update)
        queue = self._queues.setdefault(key, asyncio.Queue())
        queue.put_nowait(coroutine)
        worker = self._workers.get(key)
        if worker is None or worker.done():
            self._workers[key] = asyncio.create_task(self._drain(key), name=f"per-user-worker:{key}")

    async def _drain(self, key: Any) -> None:
        queue = self._queues[key]
        while not queue.empty():
            coroutine = queue.get_nowait()
            try:
                async with self._running:
                    await coroutine
            except Exception:
                # Handler errors are already routed to the bot's error handler inside the
                # coroutine; this only guards the queue against anything that slips through.
                logger.exception("Unhandled error while processing an update")

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        # Let in-flight updates (e.g. a send already under way) finish before exiting.
        workers = [w for w in self._workers.values() if not w.done()]
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
