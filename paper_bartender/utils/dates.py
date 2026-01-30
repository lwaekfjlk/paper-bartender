"""Date parsing utilities."""

import re
from datetime import date, timedelta
from typing import Optional

from dateutil import parser as date_parser


def parse_date(date_str: str) -> date:
    """Parse a date string into a date object.

    Supports various formats:
    - ISO format: 2025-05-10
    - US format: 5/10, 5/10/2025
    - Relative: "in 2 weeks", "in 3 days", "tomorrow", "today"
    - Natural: "next monday", "may 10"

    Args:
        date_str: The date string to parse.

    Returns:
        A date object.

    Raises:
        ValueError: If the date string cannot be parsed.
    """
    date_str = date_str.strip().lower()
    today = date.today()

    # Handle relative dates
    if date_str == 'today':
        return today

    if date_str == 'tomorrow':
        return today + timedelta(days=1)

    # Handle "in X days/weeks" format
    in_pattern = r'^in\s+(\d+)\s+(day|days|week|weeks)$'
    match = re.match(in_pattern, date_str)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit.startswith('week'):
            return today + timedelta(weeks=amount)
        return today + timedelta(days=amount)

    # Handle short date format like "5/10" (assume current year)
    short_date_pattern = r'^(\d{1,2})/(\d{1,2})$'
    match = re.match(short_date_pattern, date_str)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = today.year
        result = date(year, month, day)
        # If date has passed, assume next year
        if result < today:
            result = date(year + 1, month, day)
        return result

    # Use dateutil for other formats
    try:
        parsed = date_parser.parse(date_str, fuzzy=True)
        result = parsed.date()
        # If only month/day provided and date has passed, assume next year
        if result < today and result.year == today.year:
            # Check if year was explicitly provided
            if str(today.year) not in date_str and str(today.year)[-2:] not in date_str:
                result = date(today.year + 1, result.month, result.day)
        return result
    except (ValueError, date_parser.ParserError) as e:
        raise ValueError(f"Could not parse date: '{date_str}'") from e


def format_date(d: date) -> str:
    """Format a date for display."""
    today = date.today()
    delta = (d - today).days

    if delta == 0:
        return 'Today'
    elif delta == 1:
        return 'Tomorrow'
    elif delta == -1:
        return 'Yesterday'
    elif 0 < delta < 7:
        return f'In {delta} days ({d.strftime("%a, %b %d")})'
    elif -7 < delta < 0:
        return f'{abs(delta)} days ago ({d.strftime("%a, %b %d")})'
    else:
        return d.strftime('%a, %b %d, %Y')


def days_until(d: date) -> int:
    """Get the number of days until a date."""
    return (d - date.today()).days
