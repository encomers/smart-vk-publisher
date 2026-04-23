from abc import ABC, abstractmethod

from pydantic import HttpUrl


class IImageParser(ABC):
    @abstractmethod
    def get_images(self, text: str) -> list[HttpUrl] | None: ...
