from abc import ABC, abstractmethod


class IReader(ABC):
    @abstractmethod
    def start_reading(self) -> None: ...


class IAsyncReader(ABC):
    @abstractmethod
    async def start_reading(self) -> None: ...
