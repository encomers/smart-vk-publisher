from pydantic import BaseModel, Field, HttpUrl


class ReadyText(BaseModel):
    guid: str = Field(
        ..., description="Уникальный идентификатор текста, например, UUID"
    )
    text: str = Field(..., min_length=1, description="Весь текст поста без заголовка")
    title: str = Field(..., min_length=1, description="Заголовок поста")
    enclosure: HttpUrl | None = Field(
        ..., description="Выбранное изображение для поста"
    )
    poll_title: str | None = Field(..., description="Заголовок опроса")
    poll_options: list[str] | None = Field(..., description="Варианты ответа на опрос")
    poster_candidates: list[HttpUrl] | None = Field(
        ..., description="Выбранные изображения для поста"
    )
