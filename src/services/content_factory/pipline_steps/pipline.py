import logging

from src.model.domain import ReadyText

from ..factory import RenderStep, Step
from ..model import ContentContext, models
from .interface import IPipelineGenerator
from .llm_worker import ILLMWorker

logger = logging.getLogger(__name__)


class PipelineGenerator(IPipelineGenerator):
    def __init__(self, text_generator: ILLMWorker, image_selector: ILLMWorker) -> None:

        if text_generator is None:  # type: ignore
            raise ValueError("text_generator is None")
        if image_selector is None:  # type: ignore
            raise ValueError("image_selector is None")

        self.text_generator = text_generator
        self.image_selector = image_selector

    async def generate_themes(self, ctx: ContentContext) -> None:
        model = models.Theme  # type: ignore

    async def generate_position(self, ctx: ContentContext) -> None:
        model = models.AuthorPosition  # type: ignore

    async def select_poll(self, ctx: ContentContext) -> None:
        model = models.PollSelection  # type: ignore

    async def generate_poll(self, ctx: ContentContext) -> None:
        model = models.Poll  # type: ignore

    async def select_enclosure(self, ctx: ContentContext) -> None:
        if (
            ctx.enclosures is None
            or len(ctx.enclosures) == 0
            or ctx.themes is None
            or len(ctx.themes) == 0
        ):
            return

        enclosures = list(ctx.enclosures)

        # включаем режим "без повторов", если изображений достаточно
        no_reuse = len(enclosures) >= len(ctx.themes)

        for theme in ctx.themes:
            if theme.poll_selection or theme.poll is not None:
                continue

            try:
                enclosure = await self.image_selector.select_best_enclosure(
                    text=theme.render_prompt(),
                    images=enclosures,
                )

                theme.enclosure = enclosure

                # если можно не повторять — удаляем использованное изображение
                if no_reuse:
                    try:
                        enclosures.remove(enclosure)
                    except ValueError:
                        # на случай если модель вернула не идентичный объект из списка
                        pass

            except Exception:
                logger.exception("Error selecting enclosure")
                theme.enclosure = None

    async def generate_text(self, ctx: ContentContext) -> list[ReadyText]:
        model = ReadyText  # type: ignore

    def get_steps(self) -> list[Step]:
        return [
            self.generate_themes,
            self.generate_position,
            self.generate_style,
            self.select_poll,
            self.generate_poll,
            self.select_enclosure,
        ]

    def get_render_step(self) -> RenderStep:
        return self.generate_text
