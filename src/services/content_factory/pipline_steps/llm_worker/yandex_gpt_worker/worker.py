import asyncio
import logging
from typing import Any, Type, TypeVar

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
)
from openai.types.shared_params.response_format_json_schema import (
    ResponseFormatJSONSchema,
)
from pydantic import BaseModel, HttpUrl
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils import to_base64_image

from ....model.models import Enclosure
from ..interface import ILLMWorker
from .config import (
    YandexGPTWorkerConfig,
)

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


class YandexGPTWorker(ILLMWorker):
    """
    Интеллектуальный воркер на базе YandexGPT для полной переработки новостей.

    Класс реализует асинхронную генерацию контента (тексты, опросы, заголовки)
    и семантический подбор изображений с использованием Vision-возможностей модели.
    """

    def __init__(
        self,
        config: YandexGPTWorkerConfig,
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
        self.model_name = config.model_name.value

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
    async def send_request(
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

    async def select_best_enclosure(
        self,
        text: str,
        images: list[HttpUrl],
    ) -> HttpUrl:
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
        b64_urls = await asyncio.gather(*(to_base64_image(str(url)) for url in images))

        # Потом собираем content
        for i, b64_url in enumerate(b64_urls):
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
        result = await self.send_request(
            schema_name="enclosure_select",
            model_class=Enclosure,
            messages=messages,
            temperature=0.2,
        )

        return images[result.image_id]
