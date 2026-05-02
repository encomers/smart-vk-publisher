import logging

import vk_api  # type: ignore

from src.events import EventBus
from src.model.domain import ReadyText
from src.services.content_workers.image_generator import IImageGenerator
from src.utils import to_base64_image

from ..interface import IPublisher
from .config import VKConfig

logger = logging.getLogger(__name__)


class VKPublisher(IPublisher):
    def __init__(
        self,
        config: VKConfig,
        image_generator: IImageGenerator | None = None,
        bus: EventBus | None = None,
    ):

        try:
            self._vk = vk_api.VkApi(token=config.access_token).get_api()
        except Exception as e:
            logger.error(f"Failed to initialize VK API: {e}")
            raise

        self._config = config
        self._image_generator = image_generator
        self._bus = bus

        if self._bus:
            self._bus.subscribe(ReadyText, self.publish)  # type: ignore

        if self._config.testing_mode and self._bus:
            logger.info(
                "VKPublisher is running in testing mode. Will publish list of ready texts without scheduler and db worker."
            )
            self._bus.subscribe(list[ReadyText], self._publish_list)  # type: ignore

    async def _get_base64_image(self, text: ReadyText) -> str | None:
        """Создает base64-изображение для публикации."""

        if not text.enclosure:
            return None

        if self._image_generator:
            image = await self._image_generator.generate_from_url(
                image_url=text.enclosure,
                text=text.title,
            )
        else:
            image = await to_base64_image(text.enclosure)

        return image

    async def _publish_list(self, texts: list[ReadyText]):
        if not self._bus:
            logger.warning(
                "EventBus is not available. Cannot publish list of ready texts."
            )
            return
        for text in texts:
            self._bus.publish(text)  # type: ignore

    async def publish(self, text: ReadyText) -> str:
        """
        Публикует статью с заданным заголовком, содержанием и изображением.
        Возвращает идентификатор опубликованного поста.

        В случае ошибок на отдельных этапах (загрузка изображения, создание опроса)
        публикация продолжается без соответствующего элемента с записью в лог.
        """
        logger.info(
            f"Starting publication of article '{text.title}' (GUID: {text.guid})"
        )

        # 1. Генерация изображения
        try:
            image = await self._get_base64_image(text)
        except Exception as e:
            logger.error(f"Failed to generate image for VK post: {e}")
            image = None

        # TODO: Realise

        if image:
            return "Image got"
        return "Image not got"
