"""Tests for data models."""

from datetime import date, timedelta
from uuid import UUID

import pytest

from paper_bartender.models.milestone import Milestone, MilestoneStatus
from paper_bartender.models.paper import Paper
from paper_bartender.models.storage import StorageData
from paper_bartender.models.task import Task, TaskStatus


class TestPaper:
    """Tests for Paper model."""

    def test_create_paper(self) -> None:
        """Test creating a paper."""
        paper = Paper(
            name='My Research Paper',
            deadline=date.today() + timedelta(days=30),
            conference='NeurIPS',
        )
        assert paper.name == 'My Research Paper'
        assert paper.conference == 'NeurIPS'
        assert paper.archived is False
        assert isinstance(paper.id, UUID)

    def test_paper_defaults(self) -> None:
        """Test paper default values."""
        paper = Paper(
            name='Test',
            deadline=date.today(),
        )
        assert paper.conference is None
        assert paper.description is None
        assert paper.archived is False


class TestMilestone:
    """Tests for Milestone model."""

    def test_create_milestone(self, sample_paper: Paper) -> None:
        """Test creating a milestone."""
        milestone = Milestone(
            paper_id=sample_paper.id,
            description='Finish experiments',
            due_date=date.today() + timedelta(days=7),
        )
        assert milestone.description == 'Finish experiments'
        assert milestone.status == MilestoneStatus.PENDING
        assert milestone.decomposed is False

    def test_milestone_status_values(self) -> None:
        """Test milestone status enum values."""
        assert MilestoneStatus.PENDING.value == 'pending'
        assert MilestoneStatus.IN_PROGRESS.value == 'in_progress'
        assert MilestoneStatus.COMPLETED.value == 'completed'


class TestTask:
    """Tests for Task model."""

    def test_create_task(self, sample_paper: Paper, sample_milestone: Milestone) -> None:
        """Test creating a task."""
        task = Task(
            milestone_id=sample_milestone.id,
            paper_id=sample_paper.id,
            description='Write abstract',
            scheduled_date=date.today(),
            estimated_hours=2.0,
        )
        assert task.description == 'Write abstract'
        assert task.status == TaskStatus.PENDING
        assert task.estimated_hours == 2.0

    def test_task_status_values(self) -> None:
        """Test task status enum values."""
        assert TaskStatus.PENDING.value == 'pending'
        assert TaskStatus.COMPLETED.value == 'completed'
        assert TaskStatus.SKIPPED.value == 'skipped'


class TestStorageData:
    """Tests for StorageData model."""

    def test_empty_storage(self) -> None:
        """Test creating empty storage data."""
        data = StorageData()
        assert data.papers == []
        assert data.milestones == []
        assert data.tasks == []

    def test_storage_with_data(
        self,
        sample_paper: Paper,
        sample_milestone: Milestone,
        sample_task: Task,
    ) -> None:
        """Test storage data with items."""
        data = StorageData(
            papers=[sample_paper],
            milestones=[sample_milestone],
            tasks=[sample_task],
        )
        assert len(data.papers) == 1
        assert len(data.milestones) == 1
        assert len(data.tasks) == 1
