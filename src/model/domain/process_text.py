from pydantic import BaseModel, Field, HttpUrl


class ProcessText(BaseModel):
    guid: str = Field(
        ..., description="Уникальный идентификатор текста, например, UUID"
    )
    title: str = Field(..., min_length=1, description="Заголовок текста")
    subtitle: str = Field(..., description="Подзаголовок текста")
    content: str = Field(..., description="Основной текст")
    enclosures: list[HttpUrl] | None = Field(
        ..., description="Список всех изображений в тексте"
    )
