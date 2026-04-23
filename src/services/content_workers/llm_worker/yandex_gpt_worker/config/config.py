from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class YandexGPTWorkerConfig(BaseModel):
    accepted_models: ClassVar[list[str]] = [
        "aliceai-llm",
        "yandexgpt-5.1",
        "yandexgpt-5-pro",
        "yandexgpt-5-lite",
        "gpt-oss-120b",
        "gpt-oss-20b",
        "qwen3-235b-a22b-fp8",
        "deepseek-v32",
        "gemma-3-27b-it/latest",
    ]

    api_key: str = Field(
        ...,
        min_length=6,
        title="The API key for YandexGPT worker.",
        description="The API key for YandexGPT worker.",
    )

    folder_id: str = Field(
        ...,
        min_length=6,
        title="The folder id for YandexGPT worker.",
        description="The folder id for YandexGPT worker.",
    )

    model_name: str = Field(
        default="yandexgpt-5.1",
        title="The model name for YandexGPT worker.",
        description="The model name for YandexGPT worker.",
    )

    model_config = ConfigDict(
        extra="forbid", frozen=False, arbitrary_types_allowed=True
    )

    @field_validator("model_name")
    @classmethod
    def model_name_validator(cls, v: str) -> str:
        if v not in cls.accepted_models:
            raise ValueError(f"model_name должен быть одним из: {cls.accepted_models}")
        return v
