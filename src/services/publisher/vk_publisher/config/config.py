from pydantic import BaseModel, Field


class VKConfig(BaseModel):
    access_token: str = Field(..., description="Токен доступа к VK API", min_length=10)
    publishing_id: int = Field(
        ..., description="ID группы ВКонтакте для публикации постов"
    )
    testing_mode: bool = Field(
        default=False,
        description="Режим тестирования",
    )
