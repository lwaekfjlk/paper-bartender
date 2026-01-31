"""Paper model."""

from datetime import date
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Paper(BaseModel):
    """Represents a research paper with its deadline."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    deadline: date
    description: Optional[str] = None
    pdf_path: Optional[str] = None
    archived: bool = False

    model_config = {'frozen': False}
