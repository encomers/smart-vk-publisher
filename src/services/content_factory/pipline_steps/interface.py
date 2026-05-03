from abc import ABC, abstractmethod

from ..factory import RenderStep, Step


class IPipelineGenerator(ABC):
    @abstractmethod
    def get_steps(self) -> list[Step]: ...

    @abstractmethod
    def get_render_step(self) -> RenderStep: ...
