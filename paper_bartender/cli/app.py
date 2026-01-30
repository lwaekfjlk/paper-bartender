"""Main CLI application for paper-bartender."""

from datetime import date
from typing import Dict, List, Optional

import typer

from paper_bartender.cli.add import add_app
from paper_bartender.cli.list import list_app
from paper_bartender.models.task import Task
from paper_bartender.services.decomposition import DecompositionService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.services.task_service import TaskService
from paper_bartender.utils.dates import format_date
from paper_bartender.utils.display import (
    console,
    create_tasks_table,
    print_error,
    print_info,
    print_success,
    print_warning,
    status_style,
)

app = typer.Typer(
    name='paper-bartender',
    help='A CLI tool to help researchers manage paper deadlines',
    no_args_is_help=False,
)

app.add_typer(add_app, name='add')
app.add_typer(list_app, name='list')


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show today's tasks when no command is given."""
    if ctx.invoked_subcommand is None:
        show_today()


@app.command('today')
def today(
    all_tasks: bool = typer.Option(
        False,
        '--all',
        '-a',
        help='Show all pending tasks, not just today',
    ),
    paper: Optional[str] = typer.Option(
        None,
        '--paper',
        '-p',
        help='Filter by paper name',
    ),
) -> None:
    """Show today's tasks (or all pending tasks with --all)."""
    show_today(all_tasks=all_tasks, paper_name=paper)


def show_today(all_tasks: bool = False, paper_name: Optional[str] = None) -> None:
    """Display today's tasks."""
    task_service = TaskService()
    paper_service = PaperService()

    # Get paper filter if specified
    paper_id = None
    if paper_name:
        paper = paper_service.get_by_name(paper_name)
        if paper is None:
            print_error(f'Paper "{paper_name}" not found')
            raise typer.Exit(1)
        paper_id = paper.id

    # Get tasks
    if all_tasks:
        tasks = task_service.get_pending(paper_id)
        title = 'All Pending Tasks'
    else:
        tasks = task_service.get_today(paper_id)
        title = f"Today's Tasks ({date.today().strftime('%a, %b %d')})"

    # Check for overdue tasks
    overdue = task_service.get_overdue(paper_id)
    if overdue:
        print_warning(f'You have {len(overdue)} overdue task(s)!')
        console.print()

    if not tasks and not overdue:
        if all_tasks:
            print_info('No pending tasks. Great job!')
        else:
            print_info("No tasks scheduled for today. Use 'paper-bartender today --all' to see all pending tasks.")
        return

    # Get paper names for display
    paper_names = task_service.get_paper_name_map()

    # Show overdue tasks first
    if overdue and not all_tasks:
        overdue_table = create_tasks_table(title='Overdue Tasks')
        for task in overdue:
            p_name = paper_names.get(task.paper_id, 'Unknown')
            status = task.status.value
            hours = f'{task.estimated_hours:.1f}h' if task.estimated_hours else '-'

            overdue_table.add_row(
                p_name,
                f'[red]{task.description}[/red]',
                hours,
                f'[{status_style(status)}]{status}[/{status_style(status)}]',
            )
        console.print(overdue_table)
        console.print()

    # Show main tasks
    if tasks:
        table = create_tasks_table(title=title)
        for task in tasks:
            p_name = paper_names.get(task.paper_id, 'Unknown')
            status = task.status.value
            hours = f'{task.estimated_hours:.1f}h' if task.estimated_hours else '-'

            table.add_row(
                p_name,
                task.description,
                hours,
                f'[{status_style(status)}]{status}[/{status_style(status)}]',
            )
        console.print(table)


@app.command('decompose')
def decompose(
    paper_name: str = typer.Argument(..., help='Name of the paper'),
    force: bool = typer.Option(
        False,
        '--force',
        '-f',
        help='Re-decompose even if already decomposed',
    ),
    dry_run: bool = typer.Option(
        False,
        '--dry-run',
        '-n',
        help='Show what would be created without saving',
    ),
) -> None:
    """Decompose milestones into daily tasks using Claude AI."""
    paper_service = PaperService()
    paper = paper_service.get_by_name(paper_name)
    if paper is None:
        print_error(f'Paper "{paper_name}" not found')
        raise typer.Exit(1)

    decomposition_service = DecompositionService()

    try:
        with console.status('Generating tasks with Claude...'):
            tasks = decomposition_service.decompose_paper(
                paper.id,
                force=force,
                dry_run=dry_run,
            )
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if not tasks:
        print_warning('No milestones to decompose. Add milestones first.')
        return

    if dry_run:
        print_info('Dry run - tasks would be created:')
    else:
        print_success(f'Generated {len(tasks)} tasks')

    # Group tasks by date for display
    tasks_by_date: Dict[date, List[Task]] = {}
    for task in tasks:
        if task.scheduled_date not in tasks_by_date:
            tasks_by_date[task.scheduled_date] = []
        tasks_by_date[task.scheduled_date].append(task)

    for task_date in sorted(tasks_by_date.keys()):
        console.print(f'\n[bold]{format_date(task_date)}[/bold]')
        for task in tasks_by_date[task_date]:
            hours = f'({task.estimated_hours:.1f}h)' if task.estimated_hours else ''
            console.print(f'  - {task.description} {hours}')


if __name__ == '__main__':
    app()
