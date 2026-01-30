"""Tests for services."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from paper_bartender.config.settings import Settings
from paper_bartender.models.milestone import MilestoneStatus
from paper_bartender.models.task import TaskStatus
from paper_bartender.services.milestone_service import MilestoneService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.services.task_service import TaskService
from paper_bartender.storage.json_store import JsonStore


class TestPaperService:
    """Tests for PaperService."""

    def test_create_paper(self, test_store: JsonStore) -> None:
        """Test creating a paper."""
        service = PaperService(test_store)
        paper = service.create(
            name='Test Paper',
            deadline=date.today() + timedelta(days=30),
            conference='ICML',
        )
        assert paper.name == 'Test Paper'
        assert paper.conference == 'ICML'

    def test_create_duplicate_paper(self, test_store: JsonStore) -> None:
        """Test creating a paper with duplicate name fails."""
        service = PaperService(test_store)
        service.create(name='Test Paper', deadline=date.today())

        with pytest.raises(ValueError, match='already exists'):
            service.create(name='Test Paper', deadline=date.today())

    def test_get_by_name(self, test_store: JsonStore) -> None:
        """Test getting a paper by name."""
        service = PaperService(test_store)
        created = service.create(name='Find Me', deadline=date.today())

        found = service.get_by_name('Find Me')
        assert found is not None
        assert found.id == created.id

    def test_get_by_name_case_insensitive(self, test_store: JsonStore) -> None:
        """Test that paper lookup is case-insensitive."""
        service = PaperService(test_store)
        service.create(name='My Paper', deadline=date.today())

        found = service.get_by_name('my paper')
        assert found is not None
        assert found.name == 'My Paper'

    def test_list_papers(self, test_store: JsonStore) -> None:
        """Test listing papers."""
        service = PaperService(test_store)
        service.create(name='Paper 1', deadline=date.today() + timedelta(days=10))
        service.create(name='Paper 2', deadline=date.today() + timedelta(days=5))

        papers = service.list_all()
        assert len(papers) == 2
        # Should be sorted by deadline
        assert papers[0].name == 'Paper 2'

    def test_archive_paper(self, test_store: JsonStore) -> None:
        """Test archiving a paper."""
        service = PaperService(test_store)
        paper = service.create(name='Archive Me', deadline=date.today())

        service.archive(paper.id)
        papers = service.list_all(include_archived=False)
        assert len(papers) == 0

        papers = service.list_all(include_archived=True)
        assert len(papers) == 1


class TestMilestoneService:
    """Tests for MilestoneService."""

    def test_create_milestone(self, test_store: JsonStore) -> None:
        """Test creating a milestone."""
        paper_service = PaperService(test_store)
        paper = paper_service.create(name='Test', deadline=date.today())

        milestone_service = MilestoneService(test_store)
        milestone = milestone_service.create(
            paper_id=paper.id,
            description='Write intro',
            due_date=date.today() + timedelta(days=7),
        )
        assert milestone.description == 'Write intro'
        assert milestone.status == MilestoneStatus.PENDING

    def test_create_milestone_invalid_paper(self, test_store: JsonStore) -> None:
        """Test creating a milestone for non-existent paper fails."""
        from uuid import uuid4

        milestone_service = MilestoneService(test_store)
        with pytest.raises(ValueError, match='not found'):
            milestone_service.create(
                paper_id=uuid4(),
                description='Test',
                due_date=date.today(),
            )

    def test_list_by_paper(self, test_store: JsonStore) -> None:
        """Test listing milestones by paper."""
        paper_service = PaperService(test_store)
        paper = paper_service.create(name='Test', deadline=date.today())

        milestone_service = MilestoneService(test_store)
        milestone_service.create(paper.id, 'Task 1', date.today())
        milestone_service.create(paper.id, 'Task 2', date.today())

        milestones = milestone_service.list_by_paper(paper.id)
        assert len(milestones) == 2

    def test_complete_milestone(self, test_store: JsonStore) -> None:
        """Test completing a milestone."""
        paper_service = PaperService(test_store)
        paper = paper_service.create(name='Test', deadline=date.today())

        milestone_service = MilestoneService(test_store)
        milestone = milestone_service.create(paper.id, 'Task', date.today())

        completed = milestone_service.complete(milestone.id)
        assert completed.status == MilestoneStatus.COMPLETED


class TestTaskService:
    """Tests for TaskService."""

    def test_create_task(self, test_store: JsonStore) -> None:
        """Test creating a task."""
        paper_service = PaperService(test_store)
        paper = paper_service.create(name='Test', deadline=date.today())

        milestone_service = MilestoneService(test_store)
        milestone = milestone_service.create(paper.id, 'Milestone', date.today())

        task_service = TaskService(test_store)
        task = task_service.create(
            milestone_id=milestone.id,
            paper_id=paper.id,
            description='Do something',
            scheduled_date=date.today(),
            estimated_hours=2.0,
        )
        assert task.description == 'Do something'
        assert task.estimated_hours == 2.0

    def test_get_today(self, test_store: JsonStore) -> None:
        """Test getting today's tasks."""
        paper_service = PaperService(test_store)
        paper = paper_service.create(name='Test', deadline=date.today())

        milestone_service = MilestoneService(test_store)
        milestone = milestone_service.create(paper.id, 'Milestone', date.today())

        task_service = TaskService(test_store)
        task_service.create(milestone.id, paper.id, 'Today task', date.today())
        task_service.create(
            milestone.id, paper.id, 'Tomorrow task', date.today() + timedelta(days=1)
        )

        today_tasks = task_service.get_today()
        assert len(today_tasks) == 1
        assert today_tasks[0].description == 'Today task'

    def test_get_overdue(self, test_store: JsonStore) -> None:
        """Test getting overdue tasks."""
        paper_service = PaperService(test_store)
        paper = paper_service.create(name='Test', deadline=date.today())

        milestone_service = MilestoneService(test_store)
        milestone = milestone_service.create(paper.id, 'Milestone', date.today())

        task_service = TaskService(test_store)
        task_service.create(
            milestone.id, paper.id, 'Overdue', date.today() - timedelta(days=1)
        )
        task_service.create(milestone.id, paper.id, 'Today', date.today())

        overdue = task_service.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].description == 'Overdue'

    def test_complete_task(self, test_store: JsonStore) -> None:
        """Test completing a task."""
        paper_service = PaperService(test_store)
        paper = paper_service.create(name='Test', deadline=date.today())

        milestone_service = MilestoneService(test_store)
        milestone = milestone_service.create(paper.id, 'Milestone', date.today())

        task_service = TaskService(test_store)
        task = task_service.create(milestone.id, paper.id, 'Task', date.today())

        completed = task_service.complete(task.id)
        assert completed.status == TaskStatus.COMPLETED
