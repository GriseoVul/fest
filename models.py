
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Task:
    id: int
    title: str
    description: Optional[str]
    status: bool
    updated: datetime
    parent: Optional[int] = None     # хранит только id
    childs: List[int] = field(default_factory=list)  # только id детей
