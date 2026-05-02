import asyncio
import logging
from collections import defaultdict
from typing import Any, Type, cast

from ..interface import EventHandler, IEventBus

logger = logging.getLogger(__name__)


class EventBus(IEventBus):
    def __init__(self, *, concurrent: bool = False):
        self._handlers: dict[Type[Any], list[EventHandler[Any]]] = defaultdict(list)
        self._concurrent = concurrent
        self._tasks: set[asyncio.Task[None]] = set()
        self._stopping = False

    # -------------------------
    # SUBSCRIBE
    # -------------------------
    def subscribe(self, event_type: Type[Any], handler: EventHandler[Any]) -> None:
        if self._stopping:
            raise RuntimeError("EventBus is shutting down")
        self._handlers[event_type].append(handler)

    # -------------------------
    # PUBLISH
    # -------------------------
    async def publish(self, event: Any) -> None:
        if self._stopping:
            return

        event_type = cast(Type[Any], type(event))
        handlers = self._handlers.get(event_type, [])
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
        self, event: Any, handlers: list[EventHandler[Any]]
    ) -> None:
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                self._handle_error(e, event, handler)

    # -------------------------
    # CONCURRENT MODE
    # -------------------------
    async def _publish_concurrent(
        self, event: Any, handlers: list[EventHandler[Any]]
    ) -> None:
        tasks = [
            asyncio.create_task(self._safe_call(handler, event)) for handler in handlers
        ]
        for task in tasks:
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        await asyncio.gather(*tasks)

    async def _safe_call(self, handler: EventHandler[Any], event: Any) -> None:
        try:
            await handler(event)
        except Exception as e:
            self._handle_error(e, event, handler)

    # -------------------------
    # ERROR HANDLING
    # -------------------------
    def _handle_error(
        self, error: Exception, event: Any, handler: EventHandler[Any]
    ) -> None:
        logger.error("Error in handler %s for event %s: %s", handler, event, error)

    # -------------------------
    # SHUTDOWN
    # -------------------------
    async def shutdown(self) -> None:
        self._stopping = True

        if self._tasks:
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
