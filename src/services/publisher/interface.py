from abc import ABC, abstractmethod

from src.model.domain.ready_text import ReadyText


class IPublisher(ABC):
    @abstractmethod
    async def publish(self, text: ReadyText) -> str:
        """
        Публикует статью с заданным заголовком, содержанием и изображением.
        Возвращает идентификатор опубликованного поста.
        """
        pass
