"""Add commands for paper-bartender CLI."""

from pathlib import Path
from typing import Optional

import typer

from paper_bartender.services.decomposition import DecompositionService
from paper_bartender.services.milestone_service import MilestoneService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.utils.dates import format_date, parse_date
from paper_bartender.utils.display import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)

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
    pdf: Optional[str] = typer.Option(
        None,
        '--pdf',
        '-f',
        help='Path to the PDF file of the paper',
    ),
    description: Optional[str] = typer.Option(
        None,
        '--description',
        help='Paper description',
    ),
) -> None:
    """Add a new paper with a deadline and optional PDF."""
    try:
        deadline_date = parse_date(deadline)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)

    # Validate PDF path if provided
    pdf_path: Optional[str] = None
    if pdf:
        path = Path(pdf).expanduser().resolve()
        if not path.exists():
            print_error(f'PDF file not found: {pdf}')
            raise typer.Exit(1)
        if not path.suffix.lower() == '.pdf':
            print_error(f'Not a PDF file: {pdf}')
            raise typer.Exit(1)
        pdf_path = str(path)

    paper_service = PaperService()
    try:
        paper = paper_service.create(
            name=name,
            deadline=deadline_date,
            description=description,
            pdf_path=pdf_path,
        )
        print_success(f'Created paper "{paper.name}"')
        typer.echo(f'  Deadline: {format_date(deadline_date)}')
        if pdf_path:
            typer.echo(f'  PDF: {pdf_path}')
            # Analyze PDF sections
            try:
                from paper_bartender.utils.pdf import analyze_paper_sections
                sections = analyze_paper_sections(pdf_path)
                completed = [s for s, v in sections.items() if v]
                if completed:
                    print_info(f'  Detected sections: {", ".join(completed)}')
            except Exception:
                pass  # Silently ignore PDF analysis errors
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
    no_decompose: bool = typer.Option(
        False,
        '--no-decompose',
        help='Skip automatic task generation',
    ),
) -> None:
    """Add a milestone to a paper and automatically generate daily tasks."""
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

        # Auto-decompose the milestone unless --no-decompose is set
        if not no_decompose:
            try:
                decomposition_service = DecompositionService()
                with console.status('Generating daily tasks...'):
                    tasks = decomposition_service.decompose_milestone(milestone.id)
                print_success(f'Generated {len(tasks)} daily tasks:')
                for task in tasks:
                    hours = f'({task.estimated_hours:.1f}h)' if task.estimated_hours else ''
                    typer.echo(f'  - [{format_date(task.scheduled_date)}] {task.description} {hours}')
            except ValueError as e:
                print_warning(f'Could not auto-generate tasks: {e}')
                print_warning('You can run "paper-bartender decompose" later after setting API key')

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
