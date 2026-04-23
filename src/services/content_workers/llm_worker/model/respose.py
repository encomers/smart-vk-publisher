from pydantic import BaseModel, Field


class Text(BaseModel):
    text: str = Field(...)
    need_poll: bool = Field(...)
    enclosure: str = Field(...)


class Response(BaseModel):
    texts: list[Text] = Field(min_length=1)
