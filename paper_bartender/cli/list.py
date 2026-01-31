"""List commands for paper-bartender CLI."""

import typer

from paper_bartender.services.milestone_service import MilestoneService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.utils.dates import days_until, format_date
from paper_bartender.utils.display import (
    console,
    create_milestones_table,
    create_papers_table,
    print_error,
    print_warning,
    status_style,
)

list_app = typer.Typer(help='List papers and milestones')


@list_app.command('papers')
def list_papers(
    archived: bool = typer.Option(
        False,
        '--archived',
        '-a',
        help='Include archived papers',
    ),
) -> None:
    """List all papers."""
    paper_service = PaperService()
    papers = paper_service.list_all(include_archived=archived)

    if not papers:
        print_warning('No papers found. Use "paper-bartender add paper" to create one.')
        return

    table = create_papers_table()
    for paper in papers:
        days_left = days_until(paper.deadline)
        days_str = str(days_left) if days_left >= 0 else f'[red]{days_left}[/red]'

        table.add_row(
            paper.name,
            format_date(paper.deadline),
            days_str,
        )

    console.print(table)


@list_app.command('milestones')
def list_milestones(
    paper_name: str = typer.Argument(..., help='Name of the paper'),
    completed: bool = typer.Option(
        False,
        '--completed',
        '-c',
        help='Include completed milestones',
    ),
) -> None:
    """List milestones for a paper."""
    paper_service = PaperService()
    paper = paper_service.get_by_name(paper_name)
    if paper is None:
        print_error(f'Paper "{paper_name}" not found')
        raise typer.Exit(1)

    milestone_service = MilestoneService()
    milestones = milestone_service.list_by_paper(
        paper.id,
        include_completed=completed,
    )

    if not milestones:
        print_warning(
            f'No milestones found for "{paper.name}". '
            'Use "paper-bartender add milestone" to create one.'
        )
        return

    table = create_milestones_table(title=f'Milestones for "{paper.name}"')
    for milestone in milestones:
        status = milestone.status.value
        decomposed = '[green]Yes[/green]' if milestone.decomposed else '[yellow]No[/yellow]'

        table.add_row(
            milestone.description,
            format_date(milestone.due_date),
            f'[{status_style(status)}]{status}[/{status_style(status)}]',
            str(milestone.priority),
            decomposed,
        )

    console.print(table)
