from abc import ABC, abstractmethod

from pydantic import HttpUrl

from src.model.domain import ProcessText, ReadyText

from .model import EnclosureSelectSchema, Poll, Response, Text


class ILLMWorker(ABC):
    """
    Интерфейс для синхронного воркера LLM.

    Используется для задач, где генерация текста и опросов происходит
    в блокирующем режиме.
    """

    @abstractmethod
    def generate_text(self, text: ProcessText) -> Response:
        """Генерирует переработанный текст новости (рерайт/саммари)."""
        pass

    @abstractmethod
    def generate_poll(self, text: Text) -> Poll | None:
        """Генерирует опрос (poll) на основе содержания текста."""
        pass

    @abstractmethod
    def complete(self, text: ProcessText) -> list[ReadyText]:
        """
        Выполняет полный цикл обработки: генерация текста, опроса и
        формирование списка итоговых объектов ReadyText.
        """
        pass


class IAsyncLLMWorker(ABC):
    """
    Интерфейс для асинхронного воркера LLM.

    Рекомендуется для промышленного использования, так как генерация через API
    нейросетей является длительной I/O операцией.
    """

    @abstractmethod
    async def generate_text(self, text: ProcessText) -> Response:
        """Асинхронно генерирует переработанный текст новости."""
        pass

    @abstractmethod
    async def generate_poll(self, text: Text) -> Poll | None:
        """Асинхронно генерирует опрос к тексту."""
        pass

    @abstractmethod
    async def complete(self, text: ProcessText) -> list[ReadyText]:
        """Асинхронно выполняет полный цикл подготовки публикации."""
        pass


class IImageSelector(ABC):
    """
    Интерфейс для выбора релевантных изображений.

    Отвечает за логику сопоставления текстового контекста и визуальных данных.
    """

    @abstractmethod
    async def select_best_enclosure(
        self,
        text: str,
        images: list[HttpUrl],
    ) -> EnclosureSelectSchema:
        """
        Анализирует текст и список URL-адресов, выбирая наиболее подходящее изображение.

        Args:
            text (str): Содержание новости для анализа контекста.
            images (list[HttpUrl]): Список доступных ссылок на изображения.

        Returns:
            EnclosureSelectSchema: Объект с выбранным изображением и метаданными выбора.
        """
        ...
