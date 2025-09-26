
from __future__ import annotations

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
    parent: Optional["Task"] = None     # может быть объектом или None
    childs: List["Task"] = field(default_factory=list)  # список объектов Task
