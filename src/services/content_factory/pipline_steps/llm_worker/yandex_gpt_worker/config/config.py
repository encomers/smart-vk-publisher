from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class YandexModel(str, Enum):
    ALICEAI_LLM = "aliceai-llm"
    YANDEXGPT_5_1 = "yandexgpt-5.1"
    YANDEXGPT_5_PRO = "yandexgpt-5-pro"
    YANDEXGPT_5_LITE = "yandexgpt-5-lite"
    GPT_OSS_120B = "gpt-oss-120b"
    GPT_OSS_20B = "gpt-oss-20b"
    QWEN3_235B = "qwen3-235b-a22b-fp8"
    DEEPSEEK_V32 = "deepseek-v32"
    GEMMA_3_27B = "gemma-3-27b-it/latest"


class YandexGPTWorkerConfig(BaseModel):
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

    model_name: YandexModel = Field(
        default=YandexModel.YANDEXGPT_5_1,
        title="The model name for YandexGPT worker.",
        description="The model name for YandexGPT worker.",
    )

    model_config = ConfigDict(
        extra="forbid", frozen=False, arbitrary_types_allowed=True
    )
