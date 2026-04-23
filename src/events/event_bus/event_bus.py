import asyncio
import logging
from collections import defaultdict
from typing import Any, Type

from ..interface import EventHandler, IEventBus

logger = logging.getLogger(__name__)


class EventBus(IEventBus):
    def __init__(self, *, concurrent: bool = False):
        self._handlers: dict[Type, list[EventHandler]] = defaultdict(list)  # type: ignore
        self._concurrent = concurrent
        self._tasks: set[asyncio.Task] = set()  # type: ignore
        self._stopping = False

    # -------------------------
    # SUBSCRIBE
    # -------------------------
    def subscribe(self, event_type: Type, handler: EventHandler) -> None:  # type: ignore
        if self._stopping:
            raise RuntimeError("EventBus is shutting down")

        self._handlers[event_type].append(handler)  # type: ignore

    # -------------------------
    # PUBLISH
    # -------------------------
    async def publish(self, event: Any) -> None:
        if self._stopping:
            return

        handlers = self._handlers.get(type(event), [])  # type: ignore
        if not handlers:
            return

        if self._concurrent:
            await self._publish_concurrent(event, handlers)
        else:
            await self._publish_sequential(event, handlers)

    # -------------------------
    # SEQUENTIAL MODE
    # -------------------------
    async def _publish_sequential(
        self, event: Any, handlers: list[EventHandler]
    ) -> None:
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                await self._handle_error(e, event, handler)

    # -------------------------
    # CONCURRENT MODE
    # -------------------------
    async def _publish_concurrent(
        self, event: Any, handlers: list[EventHandler]
    ) -> None:
        tasks = []

        for handler in handlers:
            task = asyncio.create_task(self._safe_call(handler, event))
            self._tasks.add(task)  # type: ignore
            task.add_done_callback(self._tasks.discard)  # type: ignore
            tasks.append(task)  # type: ignore

        await asyncio.gather(*tasks)  # type: ignore

    async def _safe_call(self, handler: EventHandler, event: Any) -> None:
        try:
            await handler(event)
        except Exception as e:
            await self._handle_error(e, event, handler)

    # -------------------------
    # ERROR HANDLING
    # -------------------------
    async def _handle_error(
        self, error: Exception, event: Any, handler: EventHandler
    ) -> None:
        logger.error(f"Error in handler {handler} for event {event}: {error}")

    # -------------------------
    # SHUTDOWN
    # -------------------------
    async def shutdown(self) -> None:
        self._stopping = True

        if self._tasks:  # type: ignore
            await asyncio.gather(*self._tasks, return_exceptions=True)  # type: ignore
