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

# Имя логгера будет my_package.my_module
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _generate_json_schema(
    name: str, pydantic_model: Type[BaseModel]
) -> ResponseFormatJSONSchema:
    schema = pydantic_model.model_json_schema()
    return {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}


class YandexGPTWorker(IAsyncLLMWorker, IImageSelector):
    def __init__(
        self,
        config: YandexGPTWorkerConfig,
        *,
        image_selector: IImageSelector | None = None,
        bus: IEventBus | None = None,
    ) -> None:
        self.folder_id = config.folder_id
        self.model_name = config.model_name
        self.bus = bus
        self.image_selector = image_selector

        if self.bus:
            self.bus.subscribe(ProcessText, self.complete)  # type: ignore

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
        messages: list[
            ChatCompletionMessageParam
        ],  # Используем точный тип для сообщений
        temperature: float = 0.4,
    ) -> T:
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
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": theme_prompt},
            {"role": "user", "content": str(text)},
        ]

        return await self._request_json("post_themes", ThemesSchema, messages)

    async def _generate_single_text(
        self, text: ProcessText, theme: ThemeSchema
    ) -> Text:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Текст: \n\n {text}"},
            {"role": "user", "content": f"Вот тема: \n\n {theme}"},
        ]
        return await self._request_json("post_text", Text, messages)

    async def generate_text(self, text: ProcessText) -> Response:
        themes = await self._generate_themes(text)
        if len(themes.themes) == 0:
            raise Exception("No themes found")
        texts: list[Text] = []
        for theme in themes.themes:
            generated_text = await self._generate_single_text(text, theme)
            texts.append(generated_text)
        response: Response = Response(
            texts=texts,
        )
        return response

    async def generate_poll(self, text: Text) -> Poll | None:
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
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": rewrite_title_prompt},
            {"role": "user", "content": f"Текст: \n\n {text}"},
        ]
        response = await self._request_json(
            "rewrite_response", RewriteTitleSchema, messages, temperature=0.7
        )
        return response

    async def complete(self, text: ProcessText) -> list[ReadyText]:
        try:
            response = await self.generate_text(text)
            more_enclosures = (
                len(text.enclosures) >= len(response.texts)
                if text.enclosures
                else False
            )
            texts: list[ReadyText] = []
            for r_text in response.texts:
                poll_title: str | None = None
                poll_options: list[str] | None = None
                if r_text.need_poll:
                    try:
                        poll = await self.generate_poll(r_text)
                        if poll:
                            poll_title = poll.title
                            poll_options = poll.options
                    except Exception as e:
                        logger.error(
                            f"Failed to generate poll for text '{r_text.text}': {e}"
                        )

                title_object = await self.generate_title(r_text.text)

                enclosure: str | None = None

                if self.image_selector and text.enclosures and not poll_title:
                    s_img = await self.image_selector.select_best_enclosure(
                        r_text.text, text.enclosures
                    )

                    if s_img:
                        if more_enclosures:
                            enclosure = str(text.enclosures.pop(s_img.image_id))
                        else:
                            enclosure = str(text.enclosures[s_img.image_id])

                ready_text: ReadyText = ReadyText(
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

            if self.bus:
                await self.bus.publish(texts)  # type: ignore
            return texts
        except Exception as e:
            logger.error(f"Failed to complete text: {e}")
            raise
        finally:
            logger.info("Text generation process completed")

    async def select_best_enclosure(
        self,
        text: str,
        images: list[HttpUrl],
    ) -> EnclosureSelectSchema:
        if not images:
            raise ValueError("Empty images list")

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

        # 🔥 важно: конвертируем в base64
        for i, url in enumerate(images):
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

        result = await self._request_json(
            schema_name="enclosure_select",
            model_class=EnclosureSelectSchema,
            messages=messages,
            temperature=0.2,
        )

        return result
