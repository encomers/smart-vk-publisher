import logging
from typing import Callable

from src.events import IEventBus
from src.model.domain import ProcessText
from src.model.kafka import KafkaNewsMessage

from .image_parser import IImageParser
from .interface import ITextParser

logger = logging.getLogger(__name__)


class TextParser(ITextParser):
    """
    Парсер текстовых сообщений из Kafka, преобразующий сырые данные в доменную модель ProcessText.

    Слушает шину событий на наличие сырых байтов (bytes) и валидированных сообщений (KafkaNewsMessage).
    Отвечает за десериализацию, фильтрацию по условиям и извлечение медиа-вложений (изображений)
    из содержимого новостей.
    """

    def __init__(
        self,
        image_parser: IImageParser,
        event_bus: IEventBus | None,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
    ):
        """
        Инициализация парсера текста.

        Args:
            image_parser (IImageParser): Компонент для поиска и извлечения URL-адресов изображений из текста.
            event_bus (IEventBus | None): Шина событий для подписки на входящие сообщения и публикации результатов.
            parsing_condition (Callable[[KafkaNewsMessage], bool] | None, optional):
                Функция-предикат для фильтрации сообщений. Если функция возвращает False,
                сообщение игнорируется. По умолчанию None (обрабатываются все сообщения).
        """
        self.event_bus = event_bus
        self.image_parser = image_parser
        self.parsing_condition = parsing_condition

        # Регистрация обработчиков в шине событий, если она предоставлена
        if self.event_bus:
            self.event_bus.subscribe(bytes, self.parse)  # type: ignore
            self.event_bus.subscribe(KafkaNewsMessage, self.prepare)  # type: ignore

    async def parse(
        self,
        raw_text: bytes,
    ) -> KafkaNewsMessage | None:
        """
        Парсит сырые байтовые данные (JSON) в объект KafkaNewsMessage.

        Выполняет валидацию модели, проверяет сообщение через parsing_condition (если задано)
        и публикует успешно разобранный объект обратно в шину событий.

        Args:
            raw_text (bytes): Сырые данные сообщения в формате JSON.

        Returns:
            KafkaNewsMessage | None: Валидированный объект новости, либо None,
            если сообщение не прошло проверку условия `parsing_condition`.

        Raises:
            Exception: Пробрасывает исключение дальше, если валидация pydantic (model_validate_json)
            или процесс публикации завершились с ошибкой (сопровождается логированием).
        """
        try:
            # 1. Десериализация и валидация
            event = KafkaNewsMessage.model_validate_json(raw_text)

            # 2. Проверка пользовательского условия фильтрации
            if self.parsing_condition and not self.parsing_condition(event):
                return None

            # 3. Публикация валидного события дальше в пайплайн
            if self.event_bus:
                await self.event_bus.publish(event)
            return event

        except Exception as e:
            logger.error(f"Failed to parse raw text: {e}")
            raise e

    async def prepare(self, message: KafkaNewsMessage) -> ProcessText:
        """
        Формирует итоговую доменную модель ProcessText на основе KafkaNewsMessage.

        Определяет, какой текст использовать (отдает приоритет `parsed_full_text` перед `full_text`),
        собирает все медиа-вложения (ссылки из enclosure и найденные внутри текста картинки).
        Публикует результат в шину событий.

        Args:
            message (KafkaNewsMessage): Валидированное сообщение из Kafka.

        Returns:
            ProcessText: Готовая доменная модель новости со всеми извлеченными данными и вложениями.
        """
        text = message.news_item
        guid = text.guid
        title = text.title

        # Выбор наиболее полного варианта текста
        if text.parsed_full_text:
            content = text.parsed_full_text
        else:
            content = text.full_text

        subtitle = text.description

        # Извлечение изображений из самого текста
        enclouseres = self.image_parser.get_images(content)

        # Добавление главного изображения (enclosure) из метаданных, если оно существует
        if text.enclosure and text.enclosure.url:
            enclouseres = [text.enclosure.url] + (enclouseres or [])

        # Формирование доменного объекта
        process_text: ProcessText = ProcessText(
            guid=guid,
            title=title,
            content=content,
            subtitle=subtitle,
            enclosures=enclouseres,
        )

        # Передача готового объекта дальше по пайплайну
        if self.event_bus:
            await self.event_bus.publish(process_text)

        return process_text
