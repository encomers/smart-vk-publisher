from abc import ABC, abstractmethod
from typing import Type, TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, HttpUrl

T = TypeVar("T", bound=BaseModel)


class ILLMWorker(ABC):
    """
    Интерфейс для синхронного воркера LLM.

    Используется для задач, где генерация текста и опросов происходит
    в блокирующем режиме.
    """

    @abstractmethod
    async def send_request(
        self,
        schema_name: str,
        model_class: Type[T],
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.4,
    ) -> T: ...

    @abstractmethod
    async def select_best_enclosure(
        self,
        text: str,
        images: list[HttpUrl],
    ) -> HttpUrl: ...
