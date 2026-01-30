"""Storage data container model."""

from typing import List

from pydantic import BaseModel, Field

from paper_bartender.models.milestone import Milestone
from paper_bartender.models.paper import Paper
from paper_bartender.models.task import Task


class StorageData(BaseModel):
    """Container for all storage data."""

    papers: List[Paper] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)

    model_config = {'frozen': False}
