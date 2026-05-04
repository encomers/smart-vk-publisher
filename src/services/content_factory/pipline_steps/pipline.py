from src.model.domain import ReadyText

from ..factory import RenderStep, Step
from ..model import ContentContext, models
from .interface import IPipelineGenerator
from .llm_worker import ILLMWorker


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

    async def generate_style(self, ctx: ContentContext) -> None:
        model = models.PresentationStyle  # type: ignore

    async def select_poll(self, ctx: ContentContext) -> None:
        model = models.PollSelection  # type: ignore

    async def generate_poll(self, ctx: ContentContext) -> None:
        model = models.Poll  # type: ignore

    async def select_enclosure(self, ctx: ContentContext) -> None:
        model = models.Enclosure  # type: ignore

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
