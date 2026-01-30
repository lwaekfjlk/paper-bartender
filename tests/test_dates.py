"""Tests for date utilities."""

from datetime import date, timedelta

import pytest

from paper_bartender.utils.dates import days_until, format_date, parse_date


class TestParseDate:
    """Tests for parse_date function."""

    def test_parse_today(self) -> None:
        """Test parsing 'today'."""
        result = parse_date('today')
        assert result == date.today()

    def test_parse_tomorrow(self) -> None:
        """Test parsing 'tomorrow'."""
        result = parse_date('tomorrow')
        assert result == date.today() + timedelta(days=1)

    def test_parse_in_days(self) -> None:
        """Test parsing 'in X days'."""
        result = parse_date('in 5 days')
        assert result == date.today() + timedelta(days=5)

    def test_parse_in_weeks(self) -> None:
        """Test parsing 'in X weeks'."""
        result = parse_date('in 2 weeks')
        assert result == date.today() + timedelta(weeks=2)

    def test_parse_short_format(self) -> None:
        """Test parsing short date format like 5/10."""
        result = parse_date('5/10')
        assert result.month == 5
        assert result.day == 10

    def test_parse_iso_format(self) -> None:
        """Test parsing ISO format."""
        result = parse_date('2025-05-10')
        assert result == date(2025, 5, 10)

    def test_parse_invalid_date(self) -> None:
        """Test parsing invalid date string."""
        with pytest.raises(ValueError):
            parse_date('not a date')


class TestFormatDate:
    """Tests for format_date function."""

    def test_format_today(self) -> None:
        """Test formatting today's date."""
        result = format_date(date.today())
        assert result == 'Today'

    def test_format_tomorrow(self) -> None:
        """Test formatting tomorrow's date."""
        result = format_date(date.today() + timedelta(days=1))
        assert result == 'Tomorrow'

    def test_format_yesterday(self) -> None:
        """Test formatting yesterday's date."""
        result = format_date(date.today() - timedelta(days=1))
        assert result == 'Yesterday'

    def test_format_near_future(self) -> None:
        """Test formatting a date within a week."""
        result = format_date(date.today() + timedelta(days=3))
        assert 'In 3 days' in result


class TestDaysUntil:
    """Tests for days_until function."""

    def test_days_until_today(self) -> None:
        """Test days until today."""
        assert days_until(date.today()) == 0

    def test_days_until_future(self) -> None:
        """Test days until future date."""
        future = date.today() + timedelta(days=10)
        assert days_until(future) == 10

    def test_days_until_past(self) -> None:
        """Test days until past date (negative)."""
        past = date.today() - timedelta(days=5)
        assert days_until(past) == -5
