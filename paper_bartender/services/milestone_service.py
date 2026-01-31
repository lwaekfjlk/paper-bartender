"""Milestone service for CRUD operations."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from paper_bartender.models.milestone import Milestone, MilestoneStatus
from paper_bartender.storage.json_store import JsonStore


class MilestoneService:
    """Service for managing milestones."""

    def __init__(self, store: Optional[JsonStore] = None) -> None:
        """Initialize the milestone service."""
        self._store = store or JsonStore()

    def create(
        self,
        paper_id: UUID,
        description: str,
        due_date: date,
        start_date: Optional[date] = None,
        priority: int = 1,
    ) -> Milestone:
        """Create a new milestone."""
        data = self._store.load()

        # Verify paper exists
        paper_exists = any(p.id == paper_id for p in data.papers)
        if not paper_exists:
            raise ValueError(f'Paper with id {paper_id} not found')

        milestone = Milestone(
            paper_id=paper_id,
            description=description,
            start_date=start_date,
            due_date=due_date,
            priority=priority,
        )
        data.milestones.append(milestone)
        self._store.save(data)
        return milestone

    def get_by_id(self, milestone_id: UUID) -> Optional[Milestone]:
        """Get a milestone by ID."""
        data = self._store.load()
        for milestone in data.milestones:
            if milestone.id == milestone_id:
                return milestone
        return None

    def list_by_paper(
        self,
        paper_id: UUID,
        include_completed: bool = True,
    ) -> List[Milestone]:
        """List milestones for a paper."""
        data = self._store.load()
        milestones = [m for m in data.milestones if m.paper_id == paper_id]
        if not include_completed:
            milestones = [m for m in milestones if m.status != MilestoneStatus.COMPLETED]
        return sorted(milestones, key=lambda m: (m.due_date, -m.priority))

    def list_pending(self, paper_id: Optional[UUID] = None) -> List[Milestone]:
        """List pending milestones, optionally filtered by paper."""
        data = self._store.load()
        milestones = [
            m for m in data.milestones
            if m.status in (MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS)
        ]
        if paper_id:
            milestones = [m for m in milestones if m.paper_id == paper_id]
        return sorted(milestones, key=lambda m: (m.due_date, -m.priority))

    def list_not_decomposed(self, paper_id: Optional[UUID] = None) -> List[Milestone]:
        """List milestones that haven't been decomposed yet."""
        data = self._store.load()
        milestones = [
            m for m in data.milestones
            if not m.decomposed and m.status != MilestoneStatus.COMPLETED
        ]
        if paper_id:
            milestones = [m for m in milestones if m.paper_id == paper_id]
        return sorted(milestones, key=lambda m: (m.due_date, -m.priority))

    def update(self, milestone: Milestone) -> Milestone:
        """Update an existing milestone."""
        data = self._store.load()
        for i, m in enumerate(data.milestones):
            if m.id == milestone.id:
                data.milestones[i] = milestone
                self._store.save(data)
                return milestone
        raise ValueError(f'Milestone with id {milestone.id} not found')

    def mark_decomposed(self, milestone_id: UUID) -> Milestone:
        """Mark a milestone as decomposed."""
        milestone = self.get_by_id(milestone_id)
        if milestone is None:
            raise ValueError(f'Milestone with id {milestone_id} not found')
        milestone.decomposed = True
        return self.update(milestone)

    def complete(self, milestone_id: UUID) -> Milestone:
        """Mark a milestone as completed."""
        milestone = self.get_by_id(milestone_id)
        if milestone is None:
            raise ValueError(f'Milestone with id {milestone_id} not found')
        milestone.status = MilestoneStatus.COMPLETED
        return self.update(milestone)

    def delete(self, milestone_id: UUID) -> bool:
        """Delete a milestone and its associated tasks."""
        data = self._store.load()
        self._store.backup()

        original_count = len(data.milestones)
        data.milestones = [m for m in data.milestones if m.id != milestone_id]

        if len(data.milestones) == original_count:
            return False

        # Remove associated tasks
        data.tasks = [t for t in data.tasks if t.milestone_id != milestone_id]

        self._store.save(data)
        return True
