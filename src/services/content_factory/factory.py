import inspect
import logging
from typing import Awaitable, Callable, Union

from src.events import IEventBus
from src.model.domain import ReadyText
from src.model.kafka import KafkaNewsMessage
from utils import html_to_text

from .interface import IContentFactory
from .model.content_context import ContentContext
from .pipline_steps import IPipelineGenerator
from .workers import ImageParser

logger = logging.getLogger(__name__)

Step = Callable[[ContentContext], Union[None, Awaitable[None]]]
RenderStep = Callable[[ContentContext], Awaitable[list[ReadyText]]]


class AIFactory(IContentFactory):
    def __init__(
        self,
        *,
        pipeline: list[Step],
        render_step: RenderStep,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
        bus: IEventBus | None = None,
        image_parser: ImageParser | None = None,
    ) -> None:
        self.parsing_condition = parsing_condition
        self._bus = bus
        self.image_parser = image_parser or ImageParser()

        self.pipeline = pipeline
        self.render_step = render_step

        if self._bus is not None:
            self._bus.subscribe(bytes, self._complete_bytes_handler)

    @classmethod
    def from_generator(
        cls,
        *,
        generator: IPipelineGenerator,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
        bus: IEventBus | None = None,
        image_parser: ImageParser | None = None,
    ) -> AIFactory:
        pipeline = generator.get_steps()
        render_step = generator.get_render_step()

        if len(pipeline) == 0:
            logger.warning("Pipeline from generator is empty")

        if render_step is None:
            raise ValueError("Render step from generator is None")

        return cls(
            pipeline=pipeline,
            render_step=render_step,
            parsing_condition=parsing_condition,
            bus=bus,
            image_parser=image_parser,
        )

    @classmethod
    def from_pipeline(
        cls,
        *,
        render_step: RenderStep,
        processing_steps: list[Step] | None = None,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
        bus: IEventBus | None = None,
        image_parser: ImageParser | None = None,
    ) -> AIFactory:
        return cls(
            pipeline=list(processing_steps) if processing_steps else [],
            render_step=render_step,
            parsing_condition=parsing_condition,
            bus=bus,
            image_parser=image_parser,
        )

    def add_step(self, step: Step) -> None:
        self.pipeline.append(step)

    def set_render_step(self, step: RenderStep) -> None:
        self.render_step = step

    async def _complete_bytes_handler(self, event: bytes) -> None:
        try:
            data = await self.complete_data(event)
            if self._bus and data:
                await self._bus.publish(data)
        except Exception as e:
            logger.error(f"Ошибка обработки bytes: {e}")

    async def parse_bytes(self, data: bytes) -> KafkaNewsMessage | None:
        try:
            # 1. Десериализация и валидация
            event = KafkaNewsMessage.model_validate_json(data)

            # 2. Проверка пользовательского условия фильтрации
            if self.parsing_condition and not self.parsing_condition(event):
                logger.info(f"Event {event} does not pass parsing condition")
                return None

            return event

        except Exception as e:
            logger.error(f"Failed to parse raw text: {e}")
            raise e

    async def complete_message(self, message: KafkaNewsMessage) -> list[ReadyText]:

        if self.render_step is None:
            raise ValueError("Render step is not set")

        ctx = ContentContext(
            full_text="\n\n".join(
                [
                    message.news_item.title,
                    message.news_item.description,
                    html_to_text(message.news_item.full_text),
                ]
            ),
            enclosures=self.image_parser.get_images(message.news_item.full_text),
            guid=message.news_item.guid,
        )

        for step in self.pipeline:
            await run_step(step, ctx)
            if ctx.critical_error is not None:
                logger.error(
                    f"Critical error while prccessing message. Error: {ctx.critical_error}. Message: {message}"
                )
                raise ctx.critical_error

        result = await self.render_step(ctx)

        return result


async def run_step(step: Step, ctx: ContentContext) -> None:
    result = step(ctx)

    if inspect.isawaitable(result):
        await result
