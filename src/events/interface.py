from abc import ABC, abstractmethod
from typing import Any, Awaitable, Protocol, Type, TypeVar

T_contra = TypeVar("T_contra", contravariant=True)


class EventHandler(Protocol[T_contra]):
    def __call__(self, event: T_contra) -> Awaitable[None]: ...


class IEventBus(ABC):
    @abstractmethod
    def subscribe(
        self, event_type: Type[T_contra], handler: EventHandler[T_contra]
    ) -> None:  # type: ignore
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
