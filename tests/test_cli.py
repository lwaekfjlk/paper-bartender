"""Tests for CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from paper_bartender.cli.app import app
from paper_bartender.config.settings import Settings

runner = CliRunner()


@pytest.fixture
def mock_settings(temp_data_dir: Path) -> Settings:
    """Create mock settings for CLI tests."""
    return Settings(data_dir=temp_data_dir)


@pytest.fixture(autouse=True)
def use_temp_settings(mock_settings: Settings) -> None:
    """Use temporary settings for all CLI tests."""
    with patch('paper_bartender.storage.json_store.get_settings', return_value=mock_settings):
        with patch('paper_bartender.services.paper_service.JsonStore') as mock_store:
            from paper_bartender.storage.json_store import JsonStore
            mock_store.return_value = JsonStore(settings=mock_settings)
            yield


class TestHelpCommand:
    """Tests for help output."""

    def test_help(self) -> None:
        """Test --help shows usage."""
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'paper-bartender' in result.output.lower() or 'deadline' in result.output.lower()

    def test_add_help(self) -> None:
        """Test add --help shows subcommands."""
        result = runner.invoke(app, ['add', '--help'])
        assert result.exit_code == 0
        assert 'paper' in result.output.lower()
        assert 'milestone' in result.output.lower()

    def test_list_help(self) -> None:
        """Test list --help shows subcommands."""
        result = runner.invoke(app, ['list', '--help'])
        assert result.exit_code == 0
        assert 'papers' in result.output.lower()
        assert 'milestones' in result.output.lower()


class TestAddPaperCommand:
    """Tests for add paper command."""

    def test_add_paper_missing_deadline(self, temp_data_dir: Path) -> None:
        """Test add paper without deadline shows error."""
        with patch('paper_bartender.storage.json_store.get_settings') as mock:
            mock.return_value = Settings(data_dir=temp_data_dir)
            result = runner.invoke(app, ['add', 'paper', 'Test Paper'])
            assert result.exit_code != 0

    def test_add_paper_success(self, temp_data_dir: Path) -> None:
        """Test adding a paper successfully."""
        with patch('paper_bartender.storage.json_store.get_settings') as mock:
            mock.return_value = Settings(data_dir=temp_data_dir)
            result = runner.invoke(
                app, ['add', 'paper', 'Test Paper', '--deadline', 'in 2 weeks']
            )
            assert result.exit_code == 0
            assert 'Test Paper' in result.output


class TestListPapersCommand:
    """Tests for list papers command."""

    def test_list_papers_empty(self, temp_data_dir: Path) -> None:
        """Test listing papers when none exist."""
        with patch('paper_bartender.storage.json_store.get_settings') as mock:
            mock.return_value = Settings(data_dir=temp_data_dir)
            result = runner.invoke(app, ['list', 'papers'])
            assert result.exit_code == 0
            assert 'no papers' in result.output.lower()

    def test_list_papers_with_data(self, temp_data_dir: Path) -> None:
        """Test listing papers after adding one."""
        with patch('paper_bartender.storage.json_store.get_settings') as mock:
            mock.return_value = Settings(data_dir=temp_data_dir)
            # Add a paper first
            runner.invoke(
                app, ['add', 'paper', 'My Paper', '--deadline', 'in 2 weeks']
            )
            result = runner.invoke(app, ['list', 'papers'])
            assert result.exit_code == 0
            assert 'My Paper' in result.output


class TestTodayCommand:
    """Tests for today command."""

    def test_today_no_tasks(self, temp_data_dir: Path) -> None:
        """Test today command with no tasks."""
        with patch('paper_bartender.storage.json_store.get_settings') as mock:
            mock.return_value = Settings(data_dir=temp_data_dir)
            result = runner.invoke(app, ['today'])
            assert result.exit_code == 0
            assert 'no' in result.output.lower()

    def test_default_command_is_today(self, temp_data_dir: Path) -> None:
        """Test that running without command shows today's tasks."""
        with patch('paper_bartender.storage.json_store.get_settings') as mock:
            mock.return_value = Settings(data_dir=temp_data_dir)
            result = runner.invoke(app, [])
            assert result.exit_code == 0


class TestDecomposeCommand:
    """Tests for decompose command."""

    def test_decompose_paper_not_found(self, temp_data_dir: Path) -> None:
        """Test decompose with non-existent paper."""
        with patch('paper_bartender.storage.json_store.get_settings') as mock:
            mock.return_value = Settings(data_dir=temp_data_dir)
            result = runner.invoke(app, ['decompose', 'Nonexistent'])
            assert result.exit_code != 0
            assert 'not found' in result.output.lower()
