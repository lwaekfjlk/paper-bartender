"""Task model."""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    SKIPPED = 'skipped'


class Task(BaseModel):
    """Represents a daily task generated from a milestone."""

    id: UUID = Field(default_factory=uuid4)
    milestone_id: UUID
    paper_id: UUID
    description: str
    scheduled_date: date
    status: TaskStatus = TaskStatus.PENDING
    estimated_hours: Optional[float] = None

    model_config = {'frozen': False}
