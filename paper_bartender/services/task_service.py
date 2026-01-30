"""Task service for CRUD operations."""

from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from paper_bartender.models.task import Task, TaskStatus
from paper_bartender.storage.json_store import JsonStore


class TaskService:
    """Service for managing tasks."""

    def __init__(self, store: Optional[JsonStore] = None) -> None:
        """Initialize the task service."""
        self._store = store or JsonStore()

    def create(
        self,
        milestone_id: UUID,
        paper_id: UUID,
        description: str,
        scheduled_date: date,
        estimated_hours: Optional[float] = None,
    ) -> Task:
        """Create a new task."""
        data = self._store.load()

        task = Task(
            milestone_id=milestone_id,
            paper_id=paper_id,
            description=description,
            scheduled_date=scheduled_date,
            estimated_hours=estimated_hours,
        )
        data.tasks.append(task)
        self._store.save(data)
        return task

    def create_bulk(self, tasks: List[Task]) -> List[Task]:
        """Create multiple tasks at once."""
        data = self._store.load()
        data.tasks.extend(tasks)
        self._store.save(data)
        return tasks

    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        """Get a task by ID."""
        data = self._store.load()
        for task in data.tasks:
            if task.id == task_id:
                return task
        return None

    def get_by_date(
        self,
        target_date: date,
        paper_id: Optional[UUID] = None,
    ) -> List[Task]:
        """Get tasks scheduled for a specific date."""
        data = self._store.load()
        tasks = [t for t in data.tasks if t.scheduled_date == target_date]
        if paper_id:
            tasks = [t for t in tasks if t.paper_id == paper_id]
        return tasks

    def get_today(self, paper_id: Optional[UUID] = None) -> List[Task]:
        """Get today's tasks."""
        return self.get_by_date(date.today(), paper_id)

    def get_by_milestone(self, milestone_id: UUID) -> List[Task]:
        """Get all tasks for a milestone."""
        data = self._store.load()
        return [t for t in data.tasks if t.milestone_id == milestone_id]

    def get_by_paper(
        self,
        paper_id: UUID,
        include_completed: bool = True,
    ) -> List[Task]:
        """Get all tasks for a paper."""
        data = self._store.load()
        tasks = [t for t in data.tasks if t.paper_id == paper_id]
        if not include_completed:
            tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
        return sorted(tasks, key=lambda t: t.scheduled_date)

    def get_pending(self, paper_id: Optional[UUID] = None) -> List[Task]:
        """Get all pending tasks."""
        data = self._store.load()
        tasks = [
            t for t in data.tasks
            if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        ]
        if paper_id:
            tasks = [t for t in tasks if t.paper_id == paper_id]
        return sorted(tasks, key=lambda t: t.scheduled_date)

    def get_overdue(self, paper_id: Optional[UUID] = None) -> List[Task]:
        """Get overdue tasks (pending tasks with past scheduled date)."""
        today = date.today()
        data = self._store.load()
        tasks = [
            t for t in data.tasks
            if t.scheduled_date < today and t.status == TaskStatus.PENDING
        ]
        if paper_id:
            tasks = [t for t in tasks if t.paper_id == paper_id]
        return sorted(tasks, key=lambda t: t.scheduled_date)

    def update(self, task: Task) -> Task:
        """Update an existing task."""
        data = self._store.load()
        for i, t in enumerate(data.tasks):
            if t.id == task.id:
                data.tasks[i] = task
                self._store.save(data)
                return task
        raise ValueError(f'Task with id {task.id} not found')

    def complete(self, task_id: UUID) -> Task:
        """Mark a task as completed."""
        task = self.get_by_id(task_id)
        if task is None:
            raise ValueError(f'Task with id {task_id} not found')
        task.status = TaskStatus.COMPLETED
        return self.update(task)

    def skip(self, task_id: UUID) -> Task:
        """Mark a task as skipped."""
        task = self.get_by_id(task_id)
        if task is None:
            raise ValueError(f'Task with id {task_id} not found')
        task.status = TaskStatus.SKIPPED
        return self.update(task)

    def delete_by_milestone(self, milestone_id: UUID) -> int:
        """Delete all tasks for a milestone."""
        data = self._store.load()
        original_count = len(data.tasks)
        data.tasks = [t for t in data.tasks if t.milestone_id != milestone_id]
        deleted = original_count - len(data.tasks)
        if deleted > 0:
            self._store.save(data)
        return deleted

    def get_paper_name_map(self) -> Dict[UUID, str]:
        """Get a mapping of paper IDs to names."""
        data = self._store.load()
        return {p.id: p.name for p in data.papers}
