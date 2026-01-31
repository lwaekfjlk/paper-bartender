"""Display utilities using Rich."""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f'[green]✓[/green] {message}')


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f'[red]✗[/red] {message}')


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f'[yellow]![/yellow] {message}')


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f'[blue]ℹ[/blue] {message}')


def create_papers_table(title: str = 'Papers') -> Table:
    """Create a table for displaying papers."""
    table = Table(title=title, show_header=True, header_style='bold')
    table.add_column('Name', style='cyan')
    table.add_column('Deadline', style='yellow')
    table.add_column('Days Left', justify='right')
    return table


def create_milestones_table(title: str = 'Milestones') -> Table:
    """Create a table for displaying milestones."""
    table = Table(title=title, show_header=True, header_style='bold')
    table.add_column('Description', style='cyan')
    table.add_column('Due Date', style='yellow')
    table.add_column('Status', style='green')
    table.add_column('Priority', justify='right')
    table.add_column('Decomposed', justify='center')
    return table


def create_tasks_table(title: str = 'Tasks') -> Table:
    """Create a table for displaying tasks."""
    table = Table(title=title, show_header=True, header_style='bold')
    table.add_column('Paper', style='bold', width=16, no_wrap=True)
    table.add_column('Checkpoint')
    table.add_column('Detailed Task')
    return table


def status_style(status: str) -> str:
    """Get the style for a status value."""
    styles = {
        'pending': 'yellow',
        'in_progress': 'blue',
        'completed': 'green',
        'skipped': 'dim',
    }
    return styles.get(status, 'white')


# Color palette for papers (cycles through these)
PAPER_COLORS = ['cyan', 'magenta', 'green', 'yellow', 'blue', 'red']


def get_paper_color(paper_name: str, paper_colors: dict) -> str:
    """Get a consistent color for a paper name."""
    if paper_name not in paper_colors:
        color_idx = len(paper_colors) % len(PAPER_COLORS)
        paper_colors[paper_name] = PAPER_COLORS[color_idx]
    return paper_colors[paper_name]


def create_progress_bar(percentage: int, width: int = 20) -> str:
    """Create a text-based progress bar."""
    filled = int(width * percentage / 100)
    empty = width - filled
    bar = '█' * filled + '░' * empty
    return f'[green]{bar}[/green] {percentage}%'


def create_day_table(date_str: str, task_count: int) -> Table:
    """Create a table for a single day's tasks."""
    table = Table(
        title=f'[bold]{date_str}[/bold] [dim]({task_count} task{"s" if task_count != 1 else ""})[/dim]',
        title_justify='left',
        show_header=True,
        header_style='bold',
    )
    table.add_column('Paper', style='bold', width=16, no_wrap=True)
    table.add_column('Checkpoint')
    table.add_column('Detailed Task')
    return table
