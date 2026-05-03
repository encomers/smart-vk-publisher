from pydantic import BaseModel, Field


class Poll(BaseModel):
    title: str = Field(
        ...,
        description="Это поле содержит только заголовок опроса и никакой более информации",
    )
    options: list[str] = Field(
        ...,
        description="Сюда записываются только варианты ответа на опрос, здесь не содержится"
        " заголовок опроса или какая-то другая информация",
    )
