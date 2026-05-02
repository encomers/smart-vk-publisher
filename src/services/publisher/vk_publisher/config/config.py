from pydantic import BaseModel, Field


class VKConfig(BaseModel):
    access_token: str = Field(..., description="Токен доступа к VK API", min_length=10)
    group_id: int = Field(
        ..., description="ID группы ВКонтакте для публикации постов", gt=0
    )
