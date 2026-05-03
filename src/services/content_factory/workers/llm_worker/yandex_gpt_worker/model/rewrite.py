from pydantic import BaseModel, Field


class RewriteTitleSchema(BaseModel):
    title: str = Field(..., description="Сгенерированный заголовок")
