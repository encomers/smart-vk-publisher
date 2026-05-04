from pydantic import BaseModel, Field, HttpUrl


class Poll(BaseModel):
    title: str = Field(..., description="Заголовок опроса")
    options: list[str] = Field(
        ..., description="Варианты ответа", min_length=2, max_length=5
    )


class Enclosures(BaseModel):
    enclosures: list[str] = Field(..., description="Список ссылок на изображения")


class Enclosure(BaseModel):
    image_id: int = Field(..., description="ID выбранного изображения")


class Theme(BaseModel):
    title: str = Field(..., description="Заголовок темы")
    description: str = Field(
        ...,
        description="Описание темы. Указывай, чему посвящена тема, какие аспекты необходимо осветить, а какие к этой теме не относятся",
    )
    role: str = Field(
        ...,
        description="Предназначение темы. Один из вариантов: 'общее освещение темы', 'конкретный элемент темы', 'важная цитата', 'важное число'",
    )


class Themes(BaseModel):
    themes: list[Theme] = Field(
        ...,
        description="Набор тем для написания постов по статье",
        min_length=3,
        max_length=5,
    )


class AuthorPosition(BaseModel):
    tone: str = Field(..., description="Тон повествования")
    framing: str = Field(..., description="Под каким углом необходимо подавать тему")


class PollSelection(BaseModel):
    ids: list[int] = Field(
        ..., description="Список ID тем, на которые нужно сгенерировать опросы"
    )


class GeneratedText(BaseModel):
    title: str = Field(..., description="Заголовок для поста")
    content: str = Field(..., description="Основное содержание поста без заголовка")


class ThemeContext(BaseModel):
    theme: Theme = Field(..., description="Тема")
    tone: str | None = None
    framing: str | None = None
    poll_selection: bool = False
    poll: Poll | None = None
    enclosure: HttpUrl | None = None

    def render_with_task(self, task: str) -> str:
        return "\n\n".join(
            [
                "# ЗАДАЧА",
                task,
                "# КОНТЕКСТ",
                self.render_prompt(delim="##"),
            ]
        )

    def render_prompt(self, delim: str = "#") -> str:
        sections: list[str] = []

        # Основная информация о теме
        sections.append(
            "\n".join(
                [
                    f"{delim} ТЕМА ПУБЛИКАЦИИ",
                    f"Название темы: {self.theme.title}",
                    f"Описание темы: {self.theme.description}",
                    (f"Роль темы в серии публикаций: {self.theme.role}"),
                ]
            )
        )

        # Позиция / угол подачи
        if self.tone:
            sections.append(
                "\n".join(
                    [
                        f"{delim} МАНЕРА ПОДАЧИ ТЕКСТА",
                        (f"Манера подачи текста: {self.tone}."),
                    ]
                )
            )

        # С какой стороны освещать тему
        if self.framing:
            sections.append(
                "\n".join(
                    [
                        f"{delim} С КАКОЙ СТОРОНЫ ОСВЕЩАТЬ ТЕМУ",
                        (f"С какой стороны освещать тему: {self.framing}."),
                    ]
                )
            )

        # Опрос
        if self.poll_selection:
            poll_block = [
                f"{delim} ОПРОС",
                ("Для поста на эту тему будет приложен опрос."),
            ]

            if self.poll:
                poll_block.extend(
                    [
                        f"Заголовок опроса: {self.poll.title}",
                        "Варианты ответов:",
                    ]
                )

                poll_block.extend(f"- {option}" for option in self.poll.options)

            sections.append("\n".join(poll_block))

        # Изображение
        if self.enclosure:
            sections.append(
                "\n".join(
                    [
                        f"{delim} ИЗОБРАЖЕНИЕ",
                        ("Пост на эту тему будет опубликован вместе с изображением."),
                    ]
                )
            )

        return "\n\n".join(sections)

    def __str__(self) -> str:
        return self.render_prompt()
