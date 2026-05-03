from pydantic import BaseModel, Field


class EnclosureSelectSchema(BaseModel):
    image_id: int = Field(..., description="Порядковый номер изображения")
