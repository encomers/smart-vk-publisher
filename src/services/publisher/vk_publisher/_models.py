from pydantic import BaseModel, Field


class PublishingPoll(BaseModel):
    title: str = Field(..., description="Title of the poll")
    options: list[str] = Field(..., description="List of options")
