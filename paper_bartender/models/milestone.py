"""Milestone model."""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MilestoneStatus(str, Enum):
    """Status of a milestone."""

    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'


class Milestone(BaseModel):
    """Represents a milestone for a paper."""

    id: UUID = Field(default_factory=uuid4)
    paper_id: UUID
    description: str
    start_date: Optional[date] = None  # When this milestone begins (default: today or previous milestone's due_date)
    due_date: date
    status: MilestoneStatus = MilestoneStatus.PENDING
    priority: int = 1
    decomposed: bool = False

    model_config = {'frozen': False}
