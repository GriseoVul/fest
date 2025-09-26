
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Task:
    id : int
    title : str
    description : Optional[str]
    status : bool
    childs: List["Task"]