"""Domain models for Todo App."""

from enum import Enum


class Priority(str, Enum):
    """Priority level for a todo item."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
