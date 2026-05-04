from pydantic import BaseModel, Field, HttpUrl

from .models import ThemeContext


class ContentContext(BaseModel):
    full_text: str = Field(..., description="Full text of the content")
    enclosures: list[HttpUrl] | None = None
    themes: list[ThemeContext] | None = None
    critical_error: Exception | None = None
