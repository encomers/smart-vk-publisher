from abc import ABC, abstractmethod

from src.model.domain import ProcessText
from src.model.kafka import KafkaNewsMessage


class ITextParser(ABC):
    @abstractmethod
    async def parse(
        self,
        raw_text: bytes,
    ) -> KafkaNewsMessage | None: ...

    @abstractmethod
    async def prepare(self, message: KafkaNewsMessage) -> ProcessText: ...
