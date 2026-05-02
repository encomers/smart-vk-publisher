import re
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

_VERSION_RE = re.compile(r"^\d+\.\d{1,3}$")


class VKConfig(BaseModel):
    """Конфигурация для работы с VK API

    Raises:
        ValueError: в том случае, если api_version не является строкой, содержащей float
        ValueError: в том случае, если api_version меньше 5.199
        ValueError: в том случае, если api_version содержит более 3 знаков после точки
        ValueError: в том случае, если api_version не содержит float с целой и дробной частью

    Returns:
        _type_: VKConfig
    """

    access_token: str = Field(..., description="Токен доступа к VK API", min_length=10)

    publishing_id: int = Field(
        ..., description="ID группы ВКонтакте для публикации постов"
    )

    testing_mode: bool = Field(
        default=False,
        description="Режим тестирования",
    )

    api_version: str = Field(default="5.199", description="Версия API VK", min_length=1)

    @field_validator("api_version", mode="before")
    @classmethod
    def validate_api_version(cls, v: str | float | Decimal):
        # Приводим float/int/Decimal к строке до валидации поля
        if isinstance(v, Decimal):
            v = str(v)
        elif isinstance(v, float):
            # ВАЖНО: избегаем float артефактов
            v = format(v, "f")

        if not isinstance(v, str):
            raise ValueError("api_version должен быть строкой или числом")

        try:
            value = Decimal(v)
        except InvalidOperation:
            raise ValueError("api_version должен быть строкой, содержащей float")

        if value < Decimal("5.199"):
            raise ValueError("api_version должен быть не меньше 5.199")

        if not _VERSION_RE.fullmatch(v):
            raise ValueError("api_version должен содержать 1–3 знака после точки")

        return v
