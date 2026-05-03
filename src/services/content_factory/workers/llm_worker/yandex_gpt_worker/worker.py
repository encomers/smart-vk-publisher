import logging
from typing import Any, Type, TypeVar

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.shared_params.response_format_json_schema import (
    ResponseFormatJSONSchema,
)
from pydantic import BaseModel, HttpUrl
from tenacity import retry, stop_after_attempt, wait_exponential

from src.events import IEventBus
from src.model.domain import ProcessText, ReadyText
from src.utils import replace_first_line, to_base64_image

from ..interface import IAsyncLLMWorker, IImageSelector
from ..model import EnclosureSelectSchema, Poll, Response, Text
from .config import (
    YandexGPTWorkerConfig,
    poll_prompt,
    prompt,
    rewrite_title_prompt,
    theme_prompt,
)
from .model import RewriteTitleSchema, ThemeSchema, ThemesSchema

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)

# Тип-переменная для поддержки дженериков в методах валидации Pydantic
T = TypeVar("T", bound=BaseModel)


def _generate_json_schema(
    name: str, pydantic_model: Type[BaseModel]
) -> ResponseFormatJSONSchema:
    """
    Генерирует JSON-схему на основе Pydantic-модели для использования в Structured Outputs.

    Args:
        name: Уникальное имя схемы для API.
        pydantic_model: Класс модели, на основе которой строится схема.

    Returns:
        Словарь в формате ResponseFormatJSONSchema, совместимый с API OpenAI/YandexGPT.
    """
    schema = pydantic_model.model_json_schema()
    return {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}


class YandexGPTWorker(IAsyncLLMWorker, IImageSelector):
    """
    Интеллектуальный воркер на базе YandexGPT для полной переработки новостей.

    Класс реализует асинхронную генерацию контента (тексты, опросы, заголовки)
    и семантический подбор изображений с использованием Vision-возможностей модели.
    """

    def __init__(
        self,
        config: YandexGPTWorkerConfig,
        *,
        image_selector: IImageSelector | None = None,
        bus: IEventBus | None = None,
    ) -> None:
        """
        Инициализирует воркер и настраивает подписки на события.

        Args:
            config: Объект конфигурации с ключами доступа и параметрами модели.
            image_selector: Опциональный сервис выбора изображений (если не задан,
                            используется внутренняя реализация).
            bus: Шина событий для интеграции в общую цепочку обработки.
        """
        self.folder_id = config.folder_id
        self.model_name = config.model_name
        self.bus = bus
        self.image_selector = image_selector

        # Автоматическая подписка на входящие обработанные тексты
        if self.bus:
            self.bus.subscribe(ProcessText, self._complete_handler)

        # Клиент настраивается на эндпоинт Yandex Cloud с OpenAI-совместимым API
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url="https://ai.api.cloud.yandex.net/v1",
            project=config.folder_id,
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
        before_sleep=lambda rs: logger.error(
            f"Retry {rs.attempt_number}: {rs.outcome.exception() if rs.outcome else 'Unknown error'}"
        ),
    )
    async def _request_json(
        self,
        schema_name: str,
        model_class: Type[T],
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.4,
    ) -> T:
        """
        Универсальный приватный метод для выполнения запросов к LLM со структурированным выходом.

        Args:
            schema_name: Имя схемы для ответа.
            model_class: Класс Pydantic для валидации и парсинга результата.
            messages: Список сообщений диалога.
            temperature: Степень креативности модели (0.0 - 1.0).

        Returns:
            Экземпляр модели model_class с данными от нейросети.
        """
        response_format = _generate_json_schema(schema_name, model_class)

        completion: ChatCompletion = await self.client.chat.completions.create(
            model=f"gpt://{self.folder_id}/{self.model_name}",
            temperature=temperature,
            stream=False,
            messages=messages,
            response_format=response_format,
        )

        raw_content = completion.choices[0].message.content

        if raw_content is None:
            logger.error("Received empty content from LLM")
            raise ValueError("empty content")

        return model_class.model_validate_json(raw_content)

    async def _generate_themes(self, text: ProcessText) -> ThemesSchema:
        """Определяет основные темы/углы подачи для новости."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": theme_prompt},
            {"role": "user", "content": str(text)},
        ]
        return await self._request_json("post_themes", ThemesSchema, messages)

    async def _generate_single_text(
        self, text: ProcessText, theme: ThemeSchema
    ) -> Text:
        """Генерирует конкретный вариант поста по заданной теме."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Текст: \n\n {text}"},
            {"role": "user", "content": f"Вот тема: \n\n {theme}"},
        ]
        return await self._request_json("post_text", Text, messages)

    async def generate_text(self, text: ProcessText) -> Response:
        """
        Реализация генерации набора текстов.
        Сначала выделяет темы, затем для каждой генерирует пост.
        """
        themes = await self._generate_themes(text)
        if len(themes.themes) == 0:
            raise Exception("No themes found")

        texts: list[Text] = []
        for theme in themes.themes:
            generated_text = await self._generate_single_text(text, theme)
            texts.append(generated_text)

        return Response(texts=texts)

    async def generate_poll(self, text: Text) -> Poll | None:
        """Создает опрос, релевантный содержанию текста."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": poll_prompt},
            {"role": "user", "content": f"Текст: \n\n {text}"},
        ]
        try:
            return await self._request_json(
                "poll_response", Poll, messages, temperature=0.1
            )
        except Exception as e:
            logger.warning(f"Failed to generate poll: {e}")
            return None

    async def generate_title(self, text: str) -> RewriteTitleSchema:
        """Генерирует привлекательный заголовок для готового поста."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": rewrite_title_prompt},
            {"role": "user", "content": f"Текст: \n\n {text}"},
        ]
        return await self._request_json(
            "rewrite_response", RewriteTitleSchema, messages, temperature=0.7
        )

    async def _complete_handler(self, event: ProcessText) -> None:
        await self.complete(event)

    async def complete(self, text: ProcessText) -> list[ReadyText]:
        """
        Главный метод-оркестратор жизненного цикла переработки новости.

        Выполняет последовательно:
        1. Генерацию текстов по темам.
        2. Генерацию опросов (если помечено в тексте).
        3. Рерайт заголовков.
        4. Выбор лучшего изображения через Vision-механику.
        5. Публикацию готовых постов в шину.
        """
        try:
            response = await self.generate_text(text)

            # Определяем, хватит ли картинок на все тексты без повторов
            more_enclosures = (
                len(text.enclosures) >= len(response.texts)
                if text.enclosures
                else False
            )

            texts: list[ReadyText] = []

            for r_text in response.texts:
                poll_title: str | None = None
                poll_options: list[str] | None = None

                # 1. Опросы
                if r_text.need_poll:
                    try:
                        poll = await self.generate_poll(r_text)
                        if poll:
                            poll_title = poll.title
                            poll_options = poll.options
                    except Exception as e:
                        logger.error(f"Failed poll generation: {e}")

                # 2. Заголовки
                title_object = await self.generate_title(r_text.text)

                # 3. Подбор изображения
                enclosure: HttpUrl | None = None
                # Изображение выбирается только если нет опроса (частое требование платформ)
                if self.image_selector and text.enclosures and not poll_title:
                    s_img = await self.image_selector.select_best_enclosure(
                        r_text.text, text.enclosures
                    )

                    if s_img:
                        if more_enclosures:
                            # Забираем картинку из пула, чтобы она не повторялась
                            enclosure = text.enclosures.pop(s_img.image_id)
                        else:
                            # Оставляем картинку в пуле (повторное использование)
                            enclosure = text.enclosures[s_img.image_id]

                # 4. Сборка финального объекта
                ready_text = ReadyText(
                    guid=text.guid,
                    text=replace_first_line(r_text.text, "").strip(),
                    title=title_object.title,
                    enclosure=enclosure,
                    poll_title=poll_title,
                    poll_options=poll_options,
                    poster_candidates=text.enclosures.copy()
                    if text.enclosures
                    else None,
                )
                texts.append(ready_text)

            # Публикация результатов для следующих звеньев (например, Telegram Publisher)
            if self.bus:
                await self.bus.publish(texts)  # type: ignore
            return texts

        except Exception as e:
            logger.error(f"Failed to complete text processing: {e}")
            raise
        finally:
            logger.info("Text generation process completed")

    async def select_best_enclosure(
        self,
        text: str,
        images: list[HttpUrl],
    ) -> EnclosureSelectSchema:
        """
        Использует Vision-возможности модели для выбора самого релевантного изображения.

        Метод конвертирует URL в base64 и отправляет их в модель вместе с текстом.
        """
        if not images:
            raise ValueError("Empty images list")

        # Формирование мультимодального контента (текст + набор изображений)
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Ты выбираешь лучшую картинку для поста.\n"
                    "Верни только одну, которая лучше всего подходит по смыслу и визуалу.\n"
                    "Ответ строго JSON."
                ),
            },
            {"type": "text", "text": f"Текст поста:\n{text}"},
        ]

        # Добавление всех изображений в запрос
        for i, url in enumerate(images):
            # Вспомогательная функция для загрузки и кодирования в base64
            b64_url = await to_base64_image(str(url))

            content.append({"type": "text", "text": f"Изображение #{i}"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": b64_url},
                }
            )

        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "Ты эксперт по выбору изображений для соцсетей.",
            },
            {"role": "user", "content": content},  # type: ignore
        ]

        # Запрос с низкой температурой для точности выбора
        result = await self._request_json(
            schema_name="enclosure_select",
            model_class=EnclosureSelectSchema,
            messages=messages,
            temperature=0.2,
        )

        return result
