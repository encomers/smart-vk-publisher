import inspect
import logging
from typing import Awaitable, Callable, Union

from src.events import IEventBus
from src.model.domain import ReadyText
from src.model.kafka import KafkaNewsMessage

from .interface import IContentFactory
from .model.content_context import ContentContext

logger = logging.getLogger(__name__)

Step = Callable[[ContentContext], Union[None, Awaitable[None]]]
RenderStep = Callable[[ContentContext], Awaitable[list[ReadyText]]]


class AIFactory(IContentFactory):
    def __init__(
        self,
        *,
        processingSteps: list[Step] | None = None,
        renderStep: RenderStep | None = None,
        parsing_condition: Callable[[KafkaNewsMessage], bool] | None = None,
        bus: IEventBus | None = None,
    ):
        self.parsing_condition = parsing_condition
        self._bus = bus

        if self._bus:
            self._bus.subscribe(bytes, self._complete_bytes_handler)

        self.pipeline = list(processingSteps) if processingSteps else []
        self.render_step: RenderStep | None = renderStep

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
                    message.news_item.full_text,
                ]
            )
        )

        for step in self.pipeline:
            await run_step(step, ctx)

        result = await self.render_step(ctx)

        return result


async def run_step(step: Step, ctx: ContentContext) -> None:
    result = step(ctx)

    if inspect.isawaitable(result):
        await result
