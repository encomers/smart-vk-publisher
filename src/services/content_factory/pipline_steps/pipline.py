import logging

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from src.model.domain import ReadyText

from ..factory import RenderStep, Step
from ..model import ContentContext, models
from .config import prompts
from .interface import IPipelineGenerator
from .llm_worker import ILLMWorker

logger = logging.getLogger(__name__)


class PipelineGenerator(IPipelineGenerator):
    def __init__(self, text_generator: ILLMWorker, image_selector: ILLMWorker) -> None:

        if text_generator is None:  # type: ignore
            raise ValueError("text_generator is None")
        if image_selector is None:  # type: ignore
            raise ValueError("image_selector is None")

        self.text_generator = text_generator
        self.image_selector = image_selector

    async def generate_themes(self, ctx: ContentContext) -> None:
        model = models.Themes
        prompt = prompts.THEME_PROMPT
        content = "Полный текст статьи:\n\n\n" + str(ctx.full_text)
        ctx.themes = []
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=prompt),
            ChatCompletionUserMessageParam(role="user", content=content),
        ]
        try:
            result = await self.text_generator.send_request(
                schema_name="themes_schema", model_class=model, messages=messages
            )
            for theme in result.themes:
                ctx.themes.append(models.ThemeContext(theme=theme))
        except Exception as e:
            logger.exception(f"Critical error while themes generation: {e}")
            ctx.critical_error = Exception(e)

    async def generate_position(self, ctx: ContentContext) -> None:
        if ctx.themes is None or len(ctx.themes) == 0:
            logger.warning("Context themes are empty in position generation")
            return
        model = models.AuthorPosition
        prompt = prompts.AUTHOR_POSITION_PROMPT
        content = "Полный текст статьи:\n\n\n" + str(ctx.full_text)
        for theme in ctx.themes:
            theme_part = "Тема:\n\n" + theme.render_prompt()
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(role="system", content=prompt),
                ChatCompletionUserMessageParam(role="user", content=content),
                ChatCompletionUserMessageParam(role="user", content=theme_part),
            ]
            try:
                result = await self.text_generator.send_request(
                    schema_name="author_position_schema",
                    model_class=model,
                    messages=messages,
                )
                theme.tone = result.tone
                theme.framing = result.framing
            except Exception as e:
                logger.exception(f"Error in author position generation: {e}")

    async def select_poll(self, ctx: ContentContext) -> None:
        if ctx.themes is None or len(ctx.themes) == 0:
            logger.warning("Context themes are empty in poll selection")
            return
        model = models.PollSelection
        prompt = prompts.SELECT_POLL_POMPT
        content = ""
        i = 0
        for theme in ctx.themes:
            content += f"ТЕМА {i}\n\n {theme.render_prompt()}\n\n=====\n\n"
            i += 1
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=prompt),
            ChatCompletionUserMessageParam(role="user", content=content.strip()),
        ]
        try:
            result = await self.text_generator.send_request(
                schema_name="select_themes_poll_schema",
                model_class=model,
                messages=messages,
            )
        except Exception as e:
            logger.error(f"error selecting polls: {e}")
            return
        if len(result.ids) == 0 or -1 in result.ids:
            return

        for id in result.ids:
            if id < len(ctx.themes):
                ctx.themes[id].poll_selection = True

    async def generate_poll(self, ctx: ContentContext) -> None:
        if ctx.themes is None or len(ctx.themes) == 0:
            logger.warning("Context themes are empty in poll generation")
            return
        model = models.Poll
        prompt = prompts.GENERATE_POLL_PROMPT
        content = "Полный текст статьи:\n\n\n" + str(ctx.full_text)
        for theme in ctx.themes:
            if not theme.poll_selection:
                continue
            theme_part = f"Тема:\n\n{theme.render_prompt()}"
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(role="system", content=prompt),
                ChatCompletionUserMessageParam(role="user", content=content),
                ChatCompletionUserMessageParam(role="user", content=theme_part),
            ]
            try:
                result = await self.text_generator.send_request(
                    schema_name="generate_poll_schema",
                    model_class=model,
                    messages=messages,
                )
                theme.poll = result
            except Exception as e:
                logger.error(f"error generating poll: {e}")

    async def select_enclosure(self, ctx: ContentContext) -> None:
        if (
            ctx.enclosures is None
            or len(ctx.enclosures) == 0
            or ctx.themes is None
            or len(ctx.themes) == 0
        ):
            return

        enclosures = list(ctx.enclosures)

        # включаем режим "без повторов", если изображений достаточно
        no_reuse = len(enclosures) >= len(ctx.themes)

        for theme in ctx.themes:
            if theme.poll_selection or theme.poll is not None:
                continue

            try:
                enclosure = await self.image_selector.select_best_enclosure(
                    text=theme.render_prompt(),
                    images=enclosures,
                )

                theme.enclosure = enclosure

                # если можно не повторять — удаляем использованное изображение
                if no_reuse:
                    try:
                        enclosures.remove(enclosure)
                    except ValueError:
                        # на случай если модель вернула не идентичный объект из списка
                        pass

            except Exception:
                logger.exception("Error selecting enclosure")
                theme.enclosure = None

    async def generate_text(self, ctx: ContentContext) -> list[ReadyText]:
        if ctx.themes is None or len(ctx.themes) == 0:
            logger.warning("Context themes are empty in text generation")
            return []
        model = models.GeneratedText
        results: list[ReadyText] = []
        content = "Полный текст статьи:\n\n\n" + str(ctx.full_text)
        prompt = prompts.GENERATE_TEXT_PROMPT
        for theme in ctx.themes:
            if not theme.poll_selection:
                continue
            theme_part = f"Тема:\n\n{theme.render_prompt()}"
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(role="system", content=prompt),
                ChatCompletionUserMessageParam(role="user", content=content),
                ChatCompletionUserMessageParam(role="user", content=theme_part),
            ]
            try:
                result = await self.text_generator.send_request(
                    schema_name="generate_poll_schema",
                    model_class=model,
                    messages=messages,
                )
                ready_text: ReadyText = ReadyText(
                    guid=ctx.guid,
                    title=result.title,
                    text=result.content,
                    enclosure=theme.enclosure,
                    poll_title=theme.poll.title if theme.poll is not None else None,
                    poll_options=theme.poll.options if theme.poll is not None else None,
                )
                results.append(ready_text)
            except Exception as e:
                logger.error(f"error generating poll: {e}")

        return results

    def get_steps(self) -> list[Step]:
        return [
            self.generate_themes,
            self.generate_position,
            self.select_poll,
            self.generate_poll,
            self.select_enclosure,
        ]

    def get_render_step(self) -> RenderStep:
        return self.generate_text
