"""Pytest fixtures for paper-bartender tests."""

import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Generator
from uuid import uuid4

import pytest

from paper_bartender.config.settings import Settings
from paper_bartender.models.milestone import Milestone, MilestoneStatus
from paper_bartender.models.paper import Paper
from paper_bartender.models.task import Task, TaskStatus
from paper_bartender.storage.json_store import JsonStore


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings(temp_data_dir: Path) -> Settings:
    """Create test settings with temporary data directory."""
    return Settings(
        data_dir=temp_data_dir,
        anthropic_api_key='test-api-key',
    )


@pytest.fixture
def test_store(test_settings: Settings) -> JsonStore:
    """Create a JsonStore with test settings."""
    return JsonStore(settings=test_settings)


@pytest.fixture
def sample_paper() -> Paper:
    """Create a sample paper."""
    return Paper(
        id=uuid4(),
        name='Test Paper',
        deadline=date.today() + timedelta(days=30),
        description='A test paper for unit testing',
    )


@pytest.fixture
def sample_milestone(sample_paper: Paper) -> Milestone:
    """Create a sample milestone."""
    return Milestone(
        id=uuid4(),
        paper_id=sample_paper.id,
        description='Write introduction',
        due_date=date.today() + timedelta(days=14),
        priority=2,
    )


@pytest.fixture
def sample_task(sample_paper: Paper, sample_milestone: Milestone) -> Task:
    """Create a sample task."""
    return Task(
        id=uuid4(),
        milestone_id=sample_milestone.id,
        paper_id=sample_paper.id,
        description='Draft introduction outline',
        scheduled_date=date.today(),
        estimated_hours=2.0,
    )
