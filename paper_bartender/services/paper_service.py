"""Paper service for CRUD operations."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from paper_bartender.models.paper import Paper
from paper_bartender.models.storage import StorageData
from paper_bartender.storage.json_store import JsonStore


class PaperService:
    """Service for managing papers."""

    def __init__(self, store: Optional[JsonStore] = None) -> None:
        """Initialize the paper service."""
        self._store = store or JsonStore()

    def create(
        self,
        name: str,
        deadline: date,
        conference: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Paper:
        """Create a new paper."""
        data = self._store.load()

        # Check for duplicate name
        for paper in data.papers:
            if paper.name.lower() == name.lower() and not paper.archived:
                raise ValueError(f"Paper with name '{name}' already exists")

        paper = Paper(
            name=name,
            deadline=deadline,
            conference=conference,
            description=description,
        )
        data.papers.append(paper)
        self._store.save(data)
        return paper

    def get_by_id(self, paper_id: UUID) -> Optional[Paper]:
        """Get a paper by ID."""
        data = self._store.load()
        for paper in data.papers:
            if paper.id == paper_id:
                return paper
        return None

    def get_by_name(self, name: str) -> Optional[Paper]:
        """Get a paper by name (case-insensitive)."""
        data = self._store.load()
        for paper in data.papers:
            if paper.name.lower() == name.lower():
                return paper
        return None

    def list_all(self, include_archived: bool = False) -> List[Paper]:
        """List all papers."""
        data = self._store.load()
        papers = data.papers
        if not include_archived:
            papers = [p for p in papers if not p.archived]
        return sorted(papers, key=lambda p: p.deadline)

    def update(self, paper: Paper) -> Paper:
        """Update an existing paper."""
        data = self._store.load()
        for i, p in enumerate(data.papers):
            if p.id == paper.id:
                data.papers[i] = paper
                self._store.save(data)
                return paper
        raise ValueError(f'Paper with id {paper.id} not found')

    def archive(self, paper_id: UUID) -> Paper:
        """Archive a paper."""
        paper = self.get_by_id(paper_id)
        if paper is None:
            raise ValueError(f'Paper with id {paper_id} not found')
        paper.archived = True
        return self.update(paper)

    def delete(self, paper_id: UUID) -> bool:
        """Delete a paper and all associated milestones and tasks."""
        data = self._store.load()
        self._store.backup()

        # Find and remove the paper
        paper_found = False
        data.papers = [p for p in data.papers if p.id != paper_id or not (paper_found := True)]

        if not paper_found:
            # Reset paper_found check
            for p in self._store.load().papers:
                if p.id == paper_id:
                    paper_found = True
                    break

        if not paper_found:
            return False

        # Remove associated milestones
        milestone_ids = {m.id for m in data.milestones if m.paper_id == paper_id}
        data.milestones = [m for m in data.milestones if m.paper_id != paper_id]

        # Remove associated tasks
        data.tasks = [t for t in data.tasks if t.paper_id != paper_id]

        self._store.save(data)
        return True
