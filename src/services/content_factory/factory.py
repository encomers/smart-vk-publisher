import inspect
import logging
from typing import Awaitable, Callable, Union, overload

from src.events import IEventBus
from src.model.domain import ReadyText
from src.model.kafka import KafkaNewsMessage
from utils import html_to_text

from .interface import IContentFactory
from .model.content_context import ContentContext
from .pipline_steps import IPipelineGenerator
from .workers.image_parser import ImageParser

logger = logging.getLogger(__name__)

Step = Callable[[ContentContext], Union[None, Awaitable[None]]]
RenderStep = Callable[[ContentContext], Awaitable[list[ReadyText]]]


class AIFactory(IContentFactory):
    @overload
    def __init__(
        self,
        *,
        generator: IPipelineGenerator,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
        bus: IEventBus | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        processing_steps: list[Step] | None = None,
        render_step: RenderStep | None = None,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
        bus: IEventBus | None = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        generator: IPipelineGenerator | None = None,
        processing_steps: list[Step] | None = None,
        render_step: RenderStep | None = None,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
        bus: IEventBus | None = None,
    ) -> None:

        if generator is not None and (
            processing_steps is not None or render_step is not None
        ):
            raise ValueError("Use either generator OR render_step + processing_steps")

        if generator is None and render_step is None:
            raise ValueError("Either generator or render_step must be set")

        self.parsing_condition = parsing_condition
        self._bus = bus
        self.image_parser = ImageParser()

        if self._bus is not None:
            self._bus.subscribe(bytes, self._complete_bytes_handler)

        if generator is not None:
            self.pipeline = generator.get_steps()
            self.render_step = generator.get_render_step()
        else:
            self.pipeline = (
                list(processing_steps) if processing_steps is not None else []
            )
            self.render_step = render_step

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
        )

        for step in self.pipeline:
            await run_step(step, ctx)

        result = await self.render_step(ctx)

        return result


async def run_step(step: Step, ctx: ContentContext) -> None:
    result = step(ctx)

    if inspect.isawaitable(result):
        await result
