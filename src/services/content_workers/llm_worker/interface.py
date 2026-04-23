from abc import ABC, abstractmethod

from pydantic import HttpUrl

from src.model.domain import ProcessText, ReadyText

from .model import EnclosureSelectSchema, Poll, Response, Text


class ILLMWorker(ABC):
    @abstractmethod
    def generate_text(self, text: ProcessText) -> Response:
        pass

    @abstractmethod
    def generate_poll(self, text: Text) -> Poll | None:
        pass

    @abstractmethod
    def complete(self, text: ProcessText) -> list[ReadyText]:
        pass


class IAsyncLLMWorker(ABC):
    @abstractmethod
    async def generate_text(self, text: ProcessText) -> Response:
        pass

    @abstractmethod
    async def generate_poll(self, text: Text) -> Poll | None:
        pass

    @abstractmethod
    async def complete(self, text: ProcessText) -> list[ReadyText]:
        pass


class IImageSelector(ABC):
    @abstractmethod
    async def select_best_enclosure(
        self,
        text: str,
        images: list[HttpUrl],
    ) -> EnclosureSelectSchema: ...
