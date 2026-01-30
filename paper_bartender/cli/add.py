"""Add commands for paper-bartender CLI."""

from typing import Optional

import typer

from paper_bartender.services.milestone_service import MilestoneService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.utils.dates import format_date, parse_date
from paper_bartender.utils.display import print_error, print_success

add_app = typer.Typer(help='Add papers and milestones')


@add_app.command('paper')
def add_paper(
    name: str = typer.Argument(..., help='Name of the paper'),
    deadline: str = typer.Option(
        ...,
        '--deadline',
        '-d',
        help='Deadline date (e.g., 5/10, 2025-05-10, "in 2 weeks")',
    ),
    conference: Optional[str] = typer.Option(
        None,
        '--conference',
        '-c',
        help='Conference name (e.g., NeurIPS, ICML)',
    ),
    description: Optional[str] = typer.Option(
        None,
        '--description',
        help='Paper description',
    ),
) -> None:
    """Add a new paper with a deadline."""
    try:
        deadline_date = parse_date(deadline)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)

    paper_service = PaperService()
    try:
        paper = paper_service.create(
            name=name,
            deadline=deadline_date,
            conference=conference,
            description=description,
        )
        print_success(f'Created paper "{paper.name}"')
        typer.echo(f'  Deadline: {format_date(deadline_date)}')
        if conference:
            typer.echo(f'  Conference: {conference}')
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)


@add_app.command('milestone')
def add_milestone(
    paper_name: str = typer.Argument(..., help='Name of the paper'),
    description: str = typer.Argument(..., help='Milestone description'),
    due: str = typer.Option(
        ...,
        '--due',
        '-d',
        help='Due date (e.g., 5/10, 2025-05-10, "in 2 weeks")',
    ),
    priority: int = typer.Option(
        1,
        '--priority',
        '-p',
        help='Priority level (higher = more important)',
        min=1,
        max=5,
    ),
) -> None:
    """Add a milestone to a paper."""
    try:
        due_date = parse_date(due)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)

    paper_service = PaperService()
    paper = paper_service.get_by_name(paper_name)
    if paper is None:
        print_error(f'Paper "{paper_name}" not found')
        raise typer.Exit(1)

    milestone_service = MilestoneService()
    try:
        milestone = milestone_service.create(
            paper_id=paper.id,
            description=description,
            due_date=due_date,
            priority=priority,
        )
        print_success(f'Created milestone for "{paper.name}"')
        typer.echo(f'  Description: {milestone.description}')
        typer.echo(f'  Due: {format_date(due_date)}')
        typer.echo(f'  Priority: {priority}')
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
