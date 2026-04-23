import logging

from aiokafka import AIOKafkaConsumer  # type: ignore

from src.events.interface import IEventBus

from ..interface import IAsyncReader

# Инициализация логгера для мониторинга состояния потребителя
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

        # Настройка потребителя:
        # auto_offset_reset="earliest" — читать с самого начала, если смещения отсутствуют.
        # enable_auto_commit=True — автоматическое подтверждение прочтения сообщений.
        self.consumer = AIOKafkaConsumer(
            topic.strip(),
            bootstrap_servers=bootstrap_server.strip(),
            group_id=group_id.strip(),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        self.bus = bus

    async def start_reading(self) -> None:
        """
        Запускает бесконечный цикл чтения сообщений из Kafka.

        Метод открывает соединение, итерируется по входящему потоку и
        публикует содержимое сообщений (value) в шину событий.
        В случае возникновения критической ошибки логирует её и корректно
        завершает работу потребителя.
        """
        await self.consumer.start()
        logger.info("Kafka consumer started successfully.")

        try:
            async for message in self.consumer:  # type: ignore
                # Пропуск пустых сообщений (tombstones)
                if not message.value:  # type: ignore
                    continue

                logger.info(
                    f"Received message from Kafka: topic={message.topic}, "
                    f"partition={message.partition}, offset={message.offset}, "
                    f"key={message.key}, value_size={len(message.value)} bytes"  # type: ignore
                )

                # Передача сырых байтов в шину событий без десериализации.
                # Это позволяет сохранять слабую связь между транспортом и логикой.
                if self.bus:
                    await self.bus.publish(message.value)  # type: ignore

        except Exception as e:
            logger.error(f"Error reading from Kafka: {e}", exc_info=True)
        finally:
            # Гарантированное закрытие соединения при остановке сервиса
            await self.consumer.stop()
            logger.info("Kafka consumer stopped.")
