from src.model.domain import ReadyText

from ..factory import RenderStep, Step
from ..model import ContentContext
from .interface import IPipelineGenerator


class PipelineGenerator(IPipelineGenerator):
    def __init__(self) -> None: ...

    async def theme_generator(self, ctx: ContentContext) -> None: ...

    async def position_generator(self, ctx: ContentContext) -> None: ...

    async def style_generator(self, ctx: ContentContext) -> None: ...

    async def poll_selector(self, ctx: ContentContext) -> None: ...

    async def poll_generator(self, ctx: ContentContext) -> None: ...

    async def enclosure_selector(self, ctx: ContentContext) -> None: ...

    async def text_generator(self, ctx: ContentContext) -> list[ReadyText]: ...

    def get_steps(self) -> list[Step]:
        return [
            self.theme_generator,
            self.position_generator,
            self.style_generator,
            self.poll_selector,
            self.poll_generator,
            self.enclosure_selector,
        ]

    def get_render_step(self) -> RenderStep:
        return self.text_generator
