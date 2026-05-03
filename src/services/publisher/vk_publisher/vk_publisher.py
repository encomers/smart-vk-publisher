import logging
from typing import Final

import vk_api  # type: ignore

from src.events import IEventBus
from src.model.domain import ReadyText
from src.services.image_generator import IImageGenerator
from src.utils import to_base64_image

from ..interface import IPublisher
from ._models import PublishingPoll
from .config import VKConfig

logger = logging.getLogger(__name__)

_POLL_TITLE_LENGTH: Final = range(4, 61)
_POLL_OPTIONS_COUNT: Final = range(2, 11)


class VKPublisher(IPublisher):
    def __init__(
        self,
        config: VKConfig,
        image_generator: IImageGenerator | None = None,
        bus: IEventBus | None = None,
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
            self._bus.subscribe(ReadyText, self._publish_handler)

        if self._config.testing_mode and self._bus:
            logger.info(
                "VKPublisher is running in testing mode. Will publish list of ready texts without scheduler and db worker."
            )
            self._bus.subscribe(list[ReadyText], self._publish_list_handler)

    async def _get_base64_image(self, text: ReadyText) -> str | None:
        """Создает base64-изображение для публикации."""

        try:
            if not text.enclosure:
                return None

            if self._image_generator:
                image = await self._image_generator.generate_from_url(
                    image_url=str(text.enclosure),
                    text=text.title,
                )
            else:
                image = await to_base64_image(str(text.enclosure))
        except Exception as e:
            logger.error(f"Failed to generate image for VK post: {e}")
            return None

        return image

    async def _publish_list_handler(self, event: list[ReadyText]):
        if not self._bus:
            logger.warning(
                "EventBus is not available. Cannot publish list of ready texts."
            )
            return
        for text in event:
            self._bus.publish(text)  # type: ignore

    def _get_poll(self, text: ReadyText) -> PublishingPoll | None:
        title = text.poll_title.strip() if text.poll_title else None
        options = [w.strip() for w in (text.poll_options or []) if w.strip()]

        if (
            title
            and len(title) in _POLL_TITLE_LENGTH
            and len(options) in _POLL_OPTIONS_COUNT
        ):
            return PublishingPoll(title=title, options=options)

        return None

    async def _publish_handler(self, event: ReadyText) -> None:
        await self.publish(event)

    async def publish(self, text: ReadyText) -> str:
        """
        Публикует статью с заданным заголовком, содержанием и изображением/опросом.
        Возвращает идентификатор опубликованного поста.

        В случае ошибок на отдельных этапах (загрузка изображения, создание опроса)
        публикация продолжается без соответствующего элемента с записью в лог.
        """
        logger.info(
            f"Starting publication of article '{text.title}' (GUID: {text.guid})"
        )

        poll: PublishingPoll | None = self._get_poll(text)
        b64_image: str | None = await self._get_base64_image(text) if not poll else None

        # TODO: Realise

        if b64_image:
            return "Image got"
        return "Image not got"
