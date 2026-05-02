from src.model.domain import ReadyText
from src.services.content_workers.image_generator import IImageGenerator

from ..interface import IPublisher


class VKPublisher(IPublisher):
    def __init__(self, image_generator: IImageGenerator | None = None):
        self.image_generator = image_generator

    async def publish(self, text: ReadyText) -> str:

        # TODO: Реализовать публикацию в ВКонтакте через VK API
        return ""
