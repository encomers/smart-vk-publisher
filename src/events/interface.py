from abc import ABC, abstractmethod
from typing import Any, Awaitable, Protocol, Type, TypeVar

T_contra = TypeVar("T_contra", contravariant=True)


class EventHandler(Protocol[T_contra]):
    def __call__(self, event: T_contra) -> Awaitable[None]: ...


class IEventBus(ABC):
    @abstractmethod
    def subscribe(
        self, event_type: Type[T_contra], handler: "EventHandler[T_contra]"
    ) -> None:  # type: ignore[override]
        """
        Подписаться на событие определённого типа.
        """
        ...

    @abstractmethod
    def unsubscribe(
        self, event_type: Type[T_contra], handler: "EventHandler[T_contra]"
    ) -> None:  # type: ignore[override]
        """
        Отписаться от события определённого типа.
        Если хендлер не был зарегистрирован — ничего не происходит.
        """
        ...

    @abstractmethod
    async def publish(self, event: Any) -> None:
        """
        Опубликовать событие.
        Выбрасывает RuntimeError, если шина уже остановлена.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Грейсфул остановка: дождаться завершения всех запущенных обработчиков,
        после чего отклонять новые публикации и подписки.
        """
        ...
