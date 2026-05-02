import logging
from typing import cast

from aiokafka import AIOKafkaConsumer  # type: ignore[import-untyped]
from aiokafka.structs import ConsumerRecord  # type: ignore[import-untyped]

from src.events.interface import IEventBus

from ..interface import IAsyncReader

logger = logging.getLogger(__name__)


class KafkaReader(IAsyncReader):
    """
    Асинхронный потребитель (Consumer) сообщений из Apache Kafka.

    Класс инкапсулирует работу с библиотекой aiokafka и обеспечивает
    передачу сырых данных из топика во внутреннюю систему обработки через шину событий.
    """

    def __init__(
        self,
        bootstrap_server: str,
        topic: str,
        group_id: str,
        bus: IEventBus | None = None,
    ) -> None:
        """
        Инициализирует потребителя Kafka с базовыми валидациями параметров.

        Args:
            bootstrap_server (str): Адрес брокера Kafka (например, 'localhost:9092').
            topic (str): Имя топика, из которого будут читаться сообщения.
            group_id (str): Идентификатор группы потребителей для управления смещениями (offsets).
            bus (IEventBus | None): Шина событий для публикации полученных данных.

        Raises:
            ValueError: Если один из обязательных параметров пуст или содержит только пробелы.
        """
        if not bootstrap_server.strip():
            raise ValueError("Bootstrap servers list cannot be empty")
        if not topic.strip():
            raise ValueError("Topic cannot be empty")
        if not group_id.strip():
            raise ValueError("Group ID cannot be empty")

        self._consumer: AIOKafkaConsumer[bytes] = AIOKafkaConsumer(  # type: ignore[type-arg]
            topic.strip(),
            bootstrap_servers=bootstrap_server.strip(),
            group_id=group_id.strip(),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        self._bus = bus

    async def start_reading(self) -> None:
        """
        Запускает бесконечный цикл чтения сообщений из Kafka.

        Метод открывает соединение, итерируется по входящему потоку и
        публикует содержимое сообщений (value) в шину событий.
        В случае возникновения критической ошибки логирует её и корректно
        завершает работу потребителя.
        """
        await self._consumer.start()
        logger.info("Kafka consumer started successfully.")

        try:
            async for raw_message in self._consumer:  # type: ignore[attr-defined]
                message = cast(ConsumerRecord[bytes, bytes | None], raw_message)
                value = message.value

                if not value:
                    continue

                logger.info(
                    "Received message from Kafka: topic=%s, partition=%s, "
                    "offset=%s, key=%s, value_size=%d bytes",
                    message.topic,
                    message.partition,
                    message.offset,
                    message.key,
                    len(value),
                )

                if self._bus:
                    await self._bus.publish(value)

        except Exception as e:
            logger.error("Error reading from Kafka: %s", e, exc_info=True)
        finally:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped.")
