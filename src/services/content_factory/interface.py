from abc import ABC, abstractmethod

from src.model.domain import ReadyText
from src.model.kafka import KafkaNewsMessage


class IContentFactory(ABC):
    @abstractmethod
    async def parse_bytes(self, data: bytes) -> KafkaNewsMessage | None: ...

    @abstractmethod
    async def complete_message(self, message: KafkaNewsMessage) -> list[ReadyText]: ...

    async def complete_data(self, data: bytes) -> list[ReadyText] | None:
        """Парсит сырые байды в `KafkaNewsMessage`, а затем обратабывает в `list[ReadyText]`

        Args:
            data (bytes): сырые данные из Kafka

        Returns:
            list[ReadyText]: пассив готовых для публикации текстов
        """
        message = await self.parse_bytes(data)
        if not message:
            return None
        return await self.complete_message(message)
