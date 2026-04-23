from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Type

EventHandler = Callable[[Any], Awaitable[None]]


class IEventBus(ABC):
    @abstractmethod
    def subscribe(self, event_type: Type, handler: EventHandler) -> None:  # type: ignore
        """
        Подписаться на событие определённого типа
        """
        ...

    @abstractmethod
    async def publish(self, event: Any) -> None:
        """
        Опубликовать событие
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Грейсфул остановка (дождаться всех обработчиков)
        """
        ...
