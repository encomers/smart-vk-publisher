from pydantic import BaseModel, Field

from .models import ThemeContext


class ContentContext(BaseModel):
    full_text: str = Field(..., description="Full text of the content")
    themes: list[ThemeContext] | None = None
