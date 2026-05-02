import re
from decimal import Decimal
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.\d{1,3}$")
_MIN_VALUE_STR: Final = "5.199"
_MIN_VALUE: Final = Decimal(_MIN_VALUE_STR)


class VKConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str = Field(..., description="Токен доступа к VK API", min_length=10)

    publishing_id: str = Field(
        ..., description="ID группы ВКонтакте для публикации постов"
    )

    testing_mode: bool = Field(
        default=False,
        description="Режим тестирования",
    )

    api_version: str = Field(
        default=_MIN_VALUE_STR,
        description=(
            "Версия API VK. Минимум: " + _MIN_VALUE_STR + ". "
            "Допускается передача int (например, 6 → '6.0')."
        ),
        min_length=1,
    )

    @field_validator("api_version", mode="before")
    @classmethod
    def validate_api_version(cls, v: object):

        if isinstance(v, bool):
            raise ValueError("api_version не может быть bool")

        if isinstance(v, float):
            raise ValueError(
                "api_version не может быть float. Используйте str или Decimal"
            )

        if isinstance(v, int):
            if v < 0:
                raise ValueError("api_version не может быть отрицательным")
            v = f"{v}.0"
        elif isinstance(v, Decimal):
            v = str(v)

        if not isinstance(v, str):
            raise ValueError(
                f"api_version должен быть строкой формата 'X.Y', "
                f"например: {_MIN_VALUE_STR}"
            )

        v = v.strip()

        if not _VERSION_RE.fullmatch(v):
            raise ValueError(
                f"api_version должен быть в формате 'X.Y' с 1–3 знаками после точки. Например: {_MIN_VALUE_STR}"
            )

        if Decimal(v) < _MIN_VALUE:
            raise ValueError(f"api_version должен быть не меньше {_MIN_VALUE_STR}")

        return v

    @field_validator("publishing_id", mode="before")
    @classmethod
    def validate_publishing_id(cls, v: object):

        if isinstance(v, bool):
            raise ValueError("publishing_id не может быть bool")

        if isinstance(v, int):
            v = str(v)

        if not isinstance(v, str):
            raise ValueError("publishing_id должен быть строкой")

        v = v.strip()

        if not v.isascii() or not v.isdigit():
            raise ValueError("publishing_id должен быть строкой, содержащей число")

        if v == "0":
            raise ValueError("publishing_id должен быть не равен 0")

        return v
