import logging

import vk_api  # type: ignore

from src.model.domain import ReadyText
from src.services.content_workers.image_generator import IImageGenerator

from ..interface import IPublisher
from .config import VKConfig

logger = logging.getLogger(__name__)


class VKPublisher(IPublisher):
    def __init__(
        self, config: VKConfig, image_generator: IImageGenerator | None = None
    ):

        try:
            self._vk = vk_api.VkApi(token=config.access_token).get_api()
        except Exception as e:
            logger.error(f"Failed to initialize VK API: {e}")
            raise

        self._config = config
        self._image_generator = image_generator

    async def publish(self, text: ReadyText) -> str:

        # TODO: Реализовать публикацию в ВКонтакте через VK API
        return ""
