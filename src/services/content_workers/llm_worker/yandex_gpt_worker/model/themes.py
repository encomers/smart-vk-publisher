from pydantic import BaseModel, Field

class ThemeSchema(BaseModel):
    title: str = Field(...)
    description: str = Field(...)
    hook: str = Field(...)

class ThemesSchema(BaseModel):
    themes: list[ThemeSchema] = Field(...)