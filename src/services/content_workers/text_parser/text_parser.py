import logging
from typing import Callable

from src.events import IEventBus
from src.model.domain import ProcessText
from src.model.kafka import KafkaNewsMessage

from .image_parser import IImageParser
from .interface import ITextParser

logger = logging.getLogger(__name__)


class TextParser(ITextParser):
    def __init__(
        self,
        image_parser: IImageParser,
        event_bus: IEventBus | None,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
    ):
        self.event_bus = event_bus
        self.image_parser = image_parser

        self.parsing_condition = parsing_condition

        if self.event_bus:
            self.event_bus.subscribe(bytes, self.parse)  # type: ignore
            self.event_bus.subscribe(KafkaNewsMessage, self.prepare)  # type: ignore

    async def parse(
        self,
        raw_text: bytes,
    ) -> KafkaNewsMessage | None:
        try:
            # 1. parse
            event = KafkaNewsMessage.model_validate_json(raw_text)

            # 2. check condition
            if self.parsing_condition and not self.parsing_condition(event):
                return None

            # 3. publish
            if self.event_bus:
                await self.event_bus.publish(event)
            return event
        except Exception as e:
            logger.error(f"Failed to parse raw text: {e}")
            raise e

    async def prepare(self, message: KafkaNewsMessage) -> ProcessText:
        text = message.news_item
        guid = text.guid
        title = text.title

        if text.parsed_full_text:
            content = text.parsed_full_text
        else:
            content = text.full_text

        subtitle = text.description
        enclouseres = self.image_parser.get_images(content)
        if text.enclosure and text.enclosure.url:
            enclouseres = [text.enclosure.url] + (enclouseres or [])

        process_text: ProcessText = ProcessText(
            guid=guid,
            title=title,
            content=content,
            subtitle=subtitle,
            enclosures=enclouseres,
        )

        if self.event_bus:
            await self.event_bus.publish(process_text)
        return process_text
