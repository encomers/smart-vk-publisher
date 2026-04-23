import logging

from aiokafka import AIOKafkaConsumer  # type: ignore

from src.events.interface import IEventBus

from ..interface import IAsyncReader

logger = logging.getLogger(__name__)


class KafkaReader(IAsyncReader):
    def __init__(
        self,
        bootstrap_server: str,
        topic: str,
        group_id: str,
        bus: IEventBus | None = None,
    ) -> None:

        if not bootstrap_server.strip():
            raise ValueError("Bootstrap servers list cannot be empty")
        if not topic.strip():
            raise ValueError("Topic cannot be empty")
        if not group_id.strip():
            raise ValueError("Group ID cannot be empty")

        self.consumer = AIOKafkaConsumer(
            topic.strip(),
            bootstrap_servers=bootstrap_server.strip(),
            group_id=group_id.strip(),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        self.bus = bus

    async def start_reading(self) -> None:
        await self.consumer.start()
        try:
            async for message in self.consumer:  # type: ignore
                if not message.value:  # type: ignore
                    continue

                logger.info(
                    f"Received message from Kafka: topic={message.topic}, partition={message.partition}, offset={message.offset}, key={message.key}, value_size={len(message.value)} bytes"  # type: ignore
                )
                # ❗ никаких моделей тут
                if self.bus:
                    await self.bus.publish(message.value)  # type: ignore
        except Exception as e:
            logger.error(f"Error reading from Kafka: {e}")
        finally:
            await self.consumer.stop()
