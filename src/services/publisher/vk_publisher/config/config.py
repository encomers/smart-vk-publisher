import re
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator

_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.\d{1,3}$")
_MIN_VALUE_STR = "5.199"
_MIN_VALUE = Decimal(_MIN_VALUE_STR)


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

    model_config = ConfigDict(frozen=True)

    access_token: str = Field(..., description="Токен доступа к VK API", min_length=10)

    publishing_id: int = Field(
        ..., description="ID группы ВКонтакте для публикации постов"
    )

    testing_mode: bool = Field(
        default=False,
        description="Режим тестирования",
    )

    api_version: str = Field(
        default=_MIN_VALUE_STR,
        description="Версия API VK. Минимум: " + _MIN_VALUE_STR,
        min_length=1,
    )

    @field_validator("api_version", mode="before")
    @classmethod
    def validate_api_version(cls, v: object):
        # Decimal -> str
        if isinstance(v, Decimal):
            v = str(v)

        if not isinstance(v, str):
            raise ValueError(
                f"api_version должен быть строкой формата 'X.Y', "
                f"например: {_MIN_VALUE_STR}"
            )

        if not _VERSION_RE.fullmatch(v):
            raise ValueError(
                f"api_version должен быть в формате 'X.Y' с 1–3 знаками после точки. Например: {_MIN_VALUE_STR}"
            )

        try:
            value = Decimal(v)
        except InvalidOperation:
            raise ValueError(
                f"api_version должен быть строкой формата 'X.Y', например: {_MIN_VALUE_STR}"
            )

        if value < _MIN_VALUE:
            raise ValueError(f"api_version должен быть не меньше {_MIN_VALUE_STR}")

        return v
