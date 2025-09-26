from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TaskCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    status: bool

# Для ответа (рекурсивная)
class TaskSchema(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: bool
    updated: datetime = Field(default_factory=datetime.now)
    parent: Optional["TaskSchema"] = None
    childs: List["TaskSchema"] = []

    class Config:
        orm_mode = True


TaskSchema.model_rebuild()