"""Main CLI application for paper-bartender."""

from datetime import date
from typing import Dict, List, Optional

import typer

from paper_bartender.cli.add import add_app
from paper_bartender.cli.delete import delete_app
from paper_bartender.cli.list import list_app
from paper_bartender.models.task import Task
from paper_bartender.services.decomposition import DecompositionService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.services.task_service import TaskService
from paper_bartender.storage.json_store import JsonStore
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
app.add_typer(delete_app, name='delete')
app.add_typer(list_app, name='list')


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show today's tasks when no command is given."""
    if ctx.invoked_subcommand is None:
        show_today()


@app.command('today')
def today(
    paper: Optional[str] = typer.Option(
        None,
        '--paper',
        '-p',
        help='Filter by paper name',
    ),
) -> None:
    """Show today's tasks."""
    show_today(paper_name=paper)


@app.command('all')
def show_all(
    paper: Optional[str] = typer.Option(
        None,
        '--paper',
        '-p',
        help='Filter by paper name',
    ),
) -> None:
    """Show all upcoming progress by day."""
    show_upcoming(paper_name=paper)


@app.command('timeline')
def timeline(
    paper_name: str = typer.Argument(..., help='Name of the paper'),
) -> None:
    """Show the complete timeline for a specific paper."""
    show_upcoming(paper_name=paper_name)


def show_today(paper_name: Optional[str] = None) -> None:
    """Display today's tasks."""
    import re
    from paper_bartender.utils.display import get_paper_color
    from paper_bartender.services.milestone_service import MilestoneService

    task_service = TaskService()
    paper_service = PaperService()
    milestone_service = MilestoneService()

    # Get paper filter if specified
    paper_id = None
    if paper_name:
        paper = paper_service.get_by_name(paper_name)
        if paper is None:
            print_error(f'Paper "{paper_name}" not found')
            raise typer.Exit(1)
        paper_id = paper.id

    # Check for overdue tasks
    overdue = task_service.get_overdue(paper_id)
    if overdue:
        print_warning(f'You have {len(overdue)} overdue task(s)!')
        console.print()

    # Get paper names for display
    paper_names = task_service.get_paper_name_map()

    # Build milestone due date cache
    milestone_due_dates: Dict[str, date] = {}

    # Show today's tasks in detail
    tasks = task_service.get_today(paper_id)
    title = f"📋 Today's Tasks ({date.today().strftime('%a, %b %d')})"

    if not tasks and not overdue:
        print_info("No tasks scheduled for today. Use 'paper-bartender all' to see upcoming progress.")
        return

    # Show paper deadlines summary
    paper_ids_in_tasks = set(t.paper_id for t in tasks)
    if overdue:
        paper_ids_in_tasks.update(t.paper_id for t in overdue)

    papers_with_deadlines = []
    for pid in paper_ids_in_tasks:
        paper = paper_service.get_by_id(pid)
        if paper:
            days_left = (paper.deadline - date.today()).days
            papers_with_deadlines.append((paper.name, paper.deadline, days_left))

    # Sort by deadline
    papers_with_deadlines.sort(key=lambda x: x[1])

    if papers_with_deadlines:
        console.print('[bold]📌 Paper Deadlines:[/bold]')
        for p_name, deadline, days_left in papers_with_deadlines:
            if days_left < 0:
                days_str = f'[red]{abs(days_left)} days overdue[/red]'
            elif days_left == 0:
                days_str = '[red]TODAY[/red]'
            elif days_left <= 7:
                days_str = f'[yellow]{days_left} days left[/yellow]'
            else:
                days_str = f'[green]{days_left} days left[/green]'
            console.print(f'  • {p_name}: {deadline.strftime("%a, %b %d, %Y")} ({days_str})')
        console.print()

    # Track paper colors
    paper_colors: Dict[str, str] = {}

    # Cache paper deadlines
    paper_deadlines: Dict[str, tuple] = {}  # paper_id -> (deadline, days_left, progress_pct)

    def get_paper_deadline_info(paper_id) -> tuple:
        """Get paper deadline info with progress bar."""
        pid_str = str(paper_id)
        if pid_str not in paper_deadlines:
            paper = paper_service.get_by_id(paper_id)
            if paper:
                days_left = (paper.deadline - date.today()).days
                # Calculate progress: assume paper started 30 days before deadline or from today if less
                total_days = 30  # Assume 30 day project
                days_passed = total_days - days_left if days_left < total_days else 0
                progress_pct = min(100, max(0, int(days_passed * 100 / total_days))) if total_days > 0 else 0
                paper_deadlines[pid_str] = (paper.deadline, days_left, progress_pct)
            else:
                paper_deadlines[pid_str] = (None, 0, 0)
        return paper_deadlines[pid_str]

    def format_deadline_cell(paper_id) -> str:
        """Format the final deadline cell with progress bar."""
        deadline, days_left, _ = get_paper_deadline_info(paper_id)
        if deadline is None:
            return '[dim]N/A[/dim]'

        # Create time-based progress bar (how much time has passed)
        bar_width = 8
        # Color based on urgency
        if days_left < 0:
            bar = f'[red]{"█" * bar_width}[/red]'
            days_str = f'[red]{abs(days_left)}d overdue[/red]'
        elif days_left == 0:
            bar = f'[red]{"█" * bar_width}[/red]'
            days_str = '[red]TODAY![/red]'
        elif days_left <= 3:
            bar = f'[red]{"█" * bar_width}[/red]'
            days_str = f'[red]{days_left}d left[/red]'
        elif days_left <= 7:
            bar = f'[yellow]{"█" * bar_width}[/yellow]'
            days_str = f'[yellow]{days_left}d left[/yellow]'
        else:
            bar = f'[green]{"█" * bar_width}[/green]'
            days_str = f'[green]{days_left}d left[/green]'

        return f'{deadline.strftime("%m/%d")} {days_str}'

    def get_milestone_due(task: Task) -> str:
        """Get the milestone due date for a task."""
        if task.milestone_id:
            milestone_id_str = str(task.milestone_id)
            if milestone_id_str not in milestone_due_dates:
                milestone = milestone_service.get_by_id(task.milestone_id)
                if milestone:
                    milestone_due_dates[milestone_id_str] = milestone.due_date
            if milestone_id_str in milestone_due_dates:
                due = milestone_due_dates[milestone_id_str]
                days_left = (due - date.today()).days

                # Color based on urgency
                if days_left < 0:
                    days_str = f'[red]{abs(days_left)}d overdue[/red]'
                elif days_left == 0:
                    days_str = '[red]TODAY![/red]'
                elif days_left <= 3:
                    days_str = f'[red]{days_left}d left[/red]'
                elif days_left <= 7:
                    days_str = f'[yellow]{days_left}d left[/yellow]'
                else:
                    days_str = f'[green]{days_left}d left[/green]'

                return f'{due.strftime("%m/%d")} {days_str}'
        return '[dim]N/A[/dim]'

    def format_task_row(task: Task, is_overdue: bool = False) -> tuple:
        """Format a task into table row with checkpoint and detailed task."""
        p_name = paper_names.get(task.paper_id, 'Unknown')
        color = get_paper_color(p_name, paper_colors)

        # Get paper final deadline
        final_deadline = format_deadline_cell(task.paper_id)

        # Get milestone due date
        milestone_due = get_milestone_due(task)

        # Extract percentage and milestone from task description
        match = re.match(r'\[(\d+)% of \'([^\']+)\'\](.*)', task.description)
        if match:
            pct = int(match.group(1))
            milestone = match.group(2)
            detail = match.group(3).strip()

            # Create checkpoint column: progress bar + milestone name
            bar_width = 12
            filled = int(bar_width * pct / 100)
            empty = bar_width - filled
            progress_bar = f'[green]{"█" * filled}[/green][dim]{"░" * empty}[/dim]'

            checkpoint = f'{progress_bar} {pct:3d}% {milestone}'

            # Detail is the actual task description
            detailed_task = detail if detail else '[dim]N/A[/dim]'
        else:
            checkpoint = ''
            detailed_task = task.description

        if is_overdue:
            detailed_task = f'[red]{detailed_task}[/red]'

        return (
            f'[{color}]{p_name}[/{color}]',
            final_deadline,
            milestone_due,
            checkpoint,
            detailed_task,
        )

    # Show overdue tasks first
    if overdue:
        overdue_table = create_tasks_table(title='⚠️  Overdue Tasks')
        for task in overdue:
            overdue_table.add_row(*format_task_row(task, is_overdue=True))
        console.print(overdue_table)
        console.print()

    # Show today's tasks
    if tasks:
        table = create_tasks_table(title=title)
        for task in tasks:
            table.add_row(*format_task_row(task))
        console.print(table)


def show_upcoming(paper_name: Optional[str] = None) -> None:
    """Display all upcoming progress by day."""
    import re
    from paper_bartender.utils.display import create_day_table, get_paper_color
    from paper_bartender.services.milestone_service import MilestoneService

    task_service = TaskService()
    paper_service = PaperService()
    milestone_service = MilestoneService()

    # Get paper filter if specified
    paper_id = None
    if paper_name:
        paper = paper_service.get_by_name(paper_name)
        if paper is None:
            print_error(f'Paper "{paper_name}" not found')
            raise typer.Exit(1)
        paper_id = paper.id

    # Check for overdue tasks
    overdue = task_service.get_overdue(paper_id)
    if overdue:
        print_warning(f'You have {len(overdue)} overdue task(s)!')
        console.print()

    # Get paper names for display
    paper_names = task_service.get_paper_name_map()

    # Show daily progress summary
    tasks = task_service.get_pending(paper_id)
    if not tasks and not overdue:
        print_info('No pending tasks. Great job!')
        return

    # Group tasks by date
    tasks_by_date: Dict[date, List[Task]] = {}
    for task in tasks:
        if task.scheduled_date not in tasks_by_date:
            tasks_by_date[task.scheduled_date] = []
        tasks_by_date[task.scheduled_date].append(task)

    # Track paper colors for consistency
    paper_colors: Dict[str, str] = {}

    # Build milestone due date cache
    milestone_due_dates: Dict[str, date] = {}

    # Cache paper deadlines
    paper_deadlines: Dict[str, tuple] = {}

    def get_paper_deadline_info(paper_id) -> tuple:
        """Get paper deadline info."""
        pid_str = str(paper_id)
        if pid_str not in paper_deadlines:
            paper = paper_service.get_by_id(paper_id)
            if paper:
                days_left = (paper.deadline - date.today()).days
                paper_deadlines[pid_str] = (paper.deadline, days_left)
            else:
                paper_deadlines[pid_str] = (None, 0)
        return paper_deadlines[pid_str]

    def format_deadline_cell(paper_id) -> str:
        """Format the final deadline cell."""
        deadline, days_left = get_paper_deadline_info(paper_id)
        if deadline is None:
            return '[dim]N/A[/dim]'

        # Color based on urgency
        if days_left < 0:
            days_str = f'[red]{abs(days_left)}d overdue[/red]'
        elif days_left == 0:
            days_str = '[red]TODAY![/red]'
        elif days_left <= 3:
            days_str = f'[red]{days_left}d left[/red]'
        elif days_left <= 7:
            days_str = f'[yellow]{days_left}d left[/yellow]'
        else:
            days_str = f'[green]{days_left}d left[/green]'

        return f'{deadline.strftime("%m/%d")} {days_str}'

    def get_milestone_due(task: Task) -> str:
        """Get the milestone due date for a task."""
        if task.milestone_id:
            milestone_id_str = str(task.milestone_id)
            if milestone_id_str not in milestone_due_dates:
                milestone = milestone_service.get_by_id(task.milestone_id)
                if milestone:
                    milestone_due_dates[milestone_id_str] = milestone.due_date
            if milestone_id_str in milestone_due_dates:
                due = milestone_due_dates[milestone_id_str]
                days_left = (due - date.today()).days

                # Color based on urgency
                if days_left < 0:
                    days_str = f'[red]{abs(days_left)}d overdue[/red]'
                elif days_left == 0:
                    days_str = '[red]TODAY![/red]'
                elif days_left <= 3:
                    days_str = f'[red]{days_left}d left[/red]'
                elif days_left <= 7:
                    days_str = f'[yellow]{days_left}d left[/yellow]'
                else:
                    days_str = f'[green]{days_left}d left[/green]'

                return f'{due.strftime("%m/%d")} {days_str}'
        return '[dim]N/A[/dim]'

    # Calculate total stats
    total_tasks = len(tasks)
    total_days = len(tasks_by_date)

    console.print()
    console.print(f'[bold]📅 Upcoming Progress[/bold]  [dim]({total_tasks} tasks across {total_days} days)[/dim]')
    console.print()

    for task_date in sorted(tasks_by_date.keys()):
        day_tasks = tasks_by_date[task_date]
        date_str = format_date(task_date)

        table = create_day_table(date_str, len(day_tasks))

        for task in day_tasks:
            p_name = paper_names.get(task.paper_id, 'Unknown')
            color = get_paper_color(p_name, paper_colors)

            # Get paper final deadline
            final_deadline = format_deadline_cell(task.paper_id)

            # Get milestone due date
            milestone_due = get_milestone_due(task)

            # Extract percentage and milestone from task description
            match = re.match(r'\[(\d+)% of \'([^\']+)\'\](.*)', task.description)
            if match:
                pct = int(match.group(1))
                milestone = match.group(2)
                detail = match.group(3).strip()

                # Create checkpoint column: progress bar + milestone name
                bar_width = 12
                filled = int(bar_width * pct / 100)
                empty = bar_width - filled
                progress_bar = f'[green]{"█" * filled}[/green][dim]{"░" * empty}[/dim]'

                checkpoint = f'{progress_bar} {pct:3d}% {milestone}'

                # Detail is the actual task
                detail = detail if detail else '[dim]N/A[/dim]'

                table.add_row(
                    f'[{color}]{p_name}[/{color}]',
                    final_deadline,
                    milestone_due,
                    checkpoint,
                    detail,
                )
            else:
                table.add_row(
                    f'[{color}]{p_name}[/{color}]',
                    final_deadline,
                    milestone_due,
                    '',
                    task.description[:50] + '...' if len(task.description) > 50 else task.description,
                )

        console.print(table)
        console.print()


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


@app.command('done')
def done(
    task_desc: str = typer.Argument(..., help='Task description (partial match)'),
    paper_name: Optional[str] = typer.Option(
        None,
        '--paper',
        '-p',
        help='Filter by paper name',
    ),
) -> None:
    """Mark a task as completed."""
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

    # Get pending tasks
    tasks = task_service.get_pending(paper_id)

    # Find matching tasks
    matching = [t for t in tasks if task_desc.lower() in t.description.lower()]

    if not matching:
        print_error(f'No pending task matching "{task_desc}" found')
        raise typer.Exit(1)

    if len(matching) > 1:
        print_warning(f'Multiple tasks match "{task_desc}":')
        paper_names = task_service.get_paper_name_map()
        for t in matching:
            p_name = paper_names.get(t.paper_id, 'Unknown')
            typer.echo(f'  - [{p_name}] {t.description}')
        print_error('Please provide a more specific description or use --paper to filter')
        raise typer.Exit(1)

    task = matching[0]
    task_service.complete(task.id)
    print_success(f'Completed: {task.description}')


@app.command('skip')
def skip(
    task_desc: str = typer.Argument(..., help='Task description (partial match)'),
    paper_name: Optional[str] = typer.Option(
        None,
        '--paper',
        '-p',
        help='Filter by paper name',
    ),
) -> None:
    """Mark a task as skipped."""
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

    # Get pending tasks
    tasks = task_service.get_pending(paper_id)

    # Find matching tasks
    matching = [t for t in tasks if task_desc.lower() in t.description.lower()]

    if not matching:
        print_error(f'No pending task matching "{task_desc}" found')
        raise typer.Exit(1)

    if len(matching) > 1:
        print_warning(f'Multiple tasks match "{task_desc}":')
        paper_names = task_service.get_paper_name_map()
        for t in matching:
            p_name = paper_names.get(t.paper_id, 'Unknown')
            typer.echo(f'  - [{p_name}] {t.description}')
        print_error('Please provide a more specific description or use --paper to filter')
        raise typer.Exit(1)

    task = matching[0]
    task_service.skip(task.id)
    print_success(f'Skipped: {task.description}')


@app.command('clear')
def clear(
    force: bool = typer.Option(
        False,
        '--force',
        '-f',
        help='Skip confirmation prompt',
    ),
) -> None:
    """Clear all data (papers, milestones, and tasks).

    Creates a backup before clearing. Use 'paper-bartender restore' to undo.
    """
    store = JsonStore()
    data = store.load()

    # Count items
    paper_count = len([p for p in data.papers if not p.archived])
    milestone_count = len(data.milestones)
    task_count = len(data.tasks)

    if paper_count == 0 and milestone_count == 0 and task_count == 0:
        print_info('No data to clear.')
        return

    # Show what will be deleted
    print_warning(f'This will delete:')
    typer.echo(f'  - {paper_count} paper(s)')
    typer.echo(f'  - {milestone_count} milestone(s)')
    typer.echo(f'  - {task_count} task(s)')
    console.print()

    if not force:
        confirmed = typer.confirm('Are you sure you want to clear all data?')
        if not confirmed:
            print_info('Cancelled.')
            raise typer.Exit(0)

    backup_path = store.clear()
    if backup_path:
        print_success(f'All data cleared. Backup saved to: {backup_path}')
        print_info("Run 'paper-bartender restore' to undo.")
    else:
        print_success('All data cleared.')


@app.command('restore')
def restore() -> None:
    """Restore data from the most recent backup."""
    store = JsonStore()

    if store.restore_backup():
        data = store.load()
        paper_count = len([p for p in data.papers if not p.archived])
        milestone_count = len(data.milestones)
        task_count = len(data.tasks)

        print_success('Data restored from backup:')
        typer.echo(f'  - {paper_count} paper(s)')
        typer.echo(f'  - {milestone_count} milestone(s)')
        typer.echo(f'  - {task_count} task(s)')
    else:
        print_error('No backup file found.')
        raise typer.Exit(1)


@app.command('do')
def do_command(
    text: str = typer.Argument(..., help='Natural language command'),
) -> None:
    """Execute a command from natural language input.

    Examples:
        paper-bartender do "add paper ML Research deadline March 15"
        paper-bartender do "new milestone for ML Research: finish experiments by Feb 10"
    """
    from pathlib import Path

    from paper_bartender.services.milestone_service import MilestoneService
    from paper_bartender.services.nlp_parser import NLPParserService
    from paper_bartender.utils.dates import parse_date

    try:
        parser = NLPParserService()
        with console.status('Parsing command...'):
            result = parser.parse(text)
    except ValueError as e:
        print_error(f'Failed to parse: {e}')
        raise typer.Exit(1)

    command = result.get('command')
    params = result.get('params', {})

    if command == 'add_paper':
        name = params.get('name')
        deadline = params.get('deadline')
        pdf_path = params.get('pdf_path')

        if not name or not deadline:
            print_error('Could not extract paper name and deadline from input')
            raise typer.Exit(1)

        # Validate and resolve PDF path if provided
        resolved_pdf: Optional[str] = None
        if pdf_path:
            path = Path(pdf_path).expanduser().resolve()
            if path.exists() and path.suffix.lower() == '.pdf':
                resolved_pdf = str(path)
            else:
                print_warning(f'PDF not found or invalid: {pdf_path}')

        # Ask about PDF if not provided
        if not resolved_pdf:
            console.print()
            if typer.confirm('Do you have a PDF draft to link? (Required for task generation)'):
                pdf_input = typer.prompt('Enter PDF path')
                path = Path(pdf_input).expanduser().resolve()
                if path.exists() and path.suffix.lower() == '.pdf':
                    resolved_pdf = str(path)
                    print_success(f'PDF linked: {resolved_pdf}')
                else:
                    print_warning(f'PDF not found or invalid: {pdf_input}')

        paper_service = PaperService()
        try:
            deadline_date = parse_date(deadline)
            paper = paper_service.create(
                name=name,
                deadline=deadline_date,
                pdf_path=resolved_pdf,
            )
            print_success(f'Created paper "{paper.name}"')
            typer.echo(f'  Deadline: {format_date(deadline_date)}')
            if resolved_pdf:
                typer.echo(f'  PDF: {resolved_pdf}')
            else:
                print_info('Tip: Link a PDF later for more detailed, context-aware task generation')

            # Ask about milestones
            console.print()
            if typer.confirm('Would you like to add milestones now?'):
                milestone_input = typer.prompt(
                    'Describe your milestones (e.g., "finish experiments by 2/4, write results by 2/10, polish paper by 2/15")'
                )

                milestone_service = MilestoneService()

                # Try to parse multiple milestones from the input
                try:
                    with console.status('Parsing milestones...'):
                        parsed = parser.parse(f'milestones for {paper.name}: {milestone_input}')

                    if parsed.get('command') == 'add_milestones':
                        milestones_data = parsed.get('params', {}).get('milestones', [])
                    elif parsed.get('command') == 'add_milestone':
                        # Single milestone parsed
                        params = parsed.get('params', {})
                        milestones_data = [{
                            'description': params.get('description'),
                            'due_date': params.get('due_date'),
                        }]
                    else:
                        milestones_data = []

                    if not milestones_data:
                        print_warning('Could not parse milestones. Please try a clearer format.')
                    else:
                        # Sort by due_date and create with sequential start_dates
                        parsed_milestones = []
                        for ms in milestones_data:
                            desc = ms.get('description')
                            due_str = ms.get('due_date')
                            if desc and due_str:
                                try:
                                    due = parse_date(due_str)
                                    parsed_milestones.append({'description': desc, 'due_date': due})
                                except ValueError:
                                    print_warning(f'Could not parse date for "{desc}"')

                        parsed_milestones.sort(key=lambda x: x['due_date'])

                        prev_due_date = date.today()
                        total_tasks = 0
                        for ms in parsed_milestones:
                            desc = ms['description']
                            due = ms['due_date']

                            milestone = milestone_service.create(
                                paper_id=paper.id,
                                description=desc,
                                start_date=prev_due_date,
                                due_date=due,
                            )
                            print_success(f'Created milestone: {milestone.description}')
                            typer.echo(f'  Period: {format_date(prev_due_date)} → {format_date(due)}')

                            prev_due_date = due

                            # Auto-decompose milestone into tasks
                            try:
                                decomposition_service = DecompositionService()
                                with console.status(f'Generating tasks for "{desc}"...'):
                                    tasks = decomposition_service.decompose_milestone(milestone.id)
                                print_success(f'Generated {len(tasks)} daily tasks')
                                total_tasks += len(tasks)
                            except ValueError as e:
                                print_warning(f'Could not generate tasks: {e}')

                except ValueError as e:
                    print_error(f'Failed to parse milestones: {e}')

        except ValueError as e:
            print_error(str(e))
            raise typer.Exit(1)

    elif command == 'add_paper_with_milestones':
        # Create a new paper AND its milestones in one command
        name = params.get('name')
        deadline = params.get('deadline')
        pdf_path = params.get('pdf_path')
        milestones_list = params.get('milestones', [])

        if not name or not deadline:
            print_error('Could not extract paper name and deadline from input')
            raise typer.Exit(1)

        # Validate and resolve PDF path if provided
        resolved_pdf: Optional[str] = None
        if pdf_path:
            path = Path(pdf_path).expanduser().resolve()
            if path.exists() and path.suffix.lower() == '.pdf':
                resolved_pdf = str(path)
            else:
                print_warning(f'PDF not found or invalid: {pdf_path}')

        paper_service = PaperService()

        # Check if paper already exists
        existing_paper = paper_service.get_by_name(name)
        if existing_paper:
            print_warning(f'Paper "{name}" already exists. Adding milestones to existing paper.')
            target_paper = existing_paper
        else:
            # Create the paper
            try:
                deadline_date = parse_date(deadline)
                target_paper = paper_service.create(
                    name=name,
                    deadline=deadline_date,
                    pdf_path=resolved_pdf,
                )
                print_success(f'Created paper "{target_paper.name}"')
                typer.echo(f'  Deadline: {format_date(deadline_date)}')
                if resolved_pdf:
                    typer.echo(f'  PDF: {resolved_pdf}')
            except ValueError as e:
                print_error(str(e))
                raise typer.Exit(1)

        # Now create all milestones
        if milestones_list:
            milestone_service = MilestoneService()
            created_milestones = []
            total_tasks = 0

            # Parse all milestones and sort by due_date
            parsed_milestones = []
            for ms in milestones_list:
                description = ms.get('description')
                due_date_str = ms.get('due_date')

                if not description or not due_date_str:
                    print_warning(f'Skipping incomplete milestone: {ms}')
                    continue

                try:
                    due = parse_date(due_date_str)
                    parsed_milestones.append({'description': description, 'due_date': due})
                except ValueError as e:
                    print_error(f'Failed to parse date for "{description}": {e}')

            # Sort milestones by due_date to ensure sequential ordering
            parsed_milestones.sort(key=lambda x: x['due_date'])

            # Create milestones with proper start_date (sequential)
            prev_due_date = date.today()
            for ms in parsed_milestones:
                description = ms['description']
                due = ms['due_date']

                try:
                    milestone = milestone_service.create(
                        paper_id=target_paper.id,
                        description=description,
                        start_date=prev_due_date,
                        due_date=due,
                    )
                    created_milestones.append(milestone)
                    print_success(f'Created milestone: {milestone.description}')
                    typer.echo(f'  Period: {format_date(prev_due_date)} → {format_date(due)}')

                    # Update prev_due_date for next milestone
                    prev_due_date = due

                    # Auto-decompose milestone into tasks
                    try:
                        decomposition_service = DecompositionService()
                        with console.status(f'Generating tasks for "{description}"...'):
                            tasks = decomposition_service.decompose_milestone(milestone.id)
                        print_success(f'Generated {len(tasks)} daily tasks')
                        total_tasks += len(tasks)
                    except ValueError as e:
                        print_warning(f'Could not auto-generate tasks: {e}')

                except ValueError as e:
                    print_error(f'Failed to create milestone "{description}": {e}')

            if created_milestones:
                console.print()
                print_success(f'Created {len(created_milestones)} milestone(s) with {total_tasks} total tasks')

    elif command == 'add_milestone':
        paper_name = params.get('paper_name')
        description = params.get('description')
        due_date = params.get('due_date')

        if not paper_name or not description or not due_date:
            print_error('Could not extract paper name, description, and due date from input')
            raise typer.Exit(1)

        paper_svc = PaperService()
        target_paper = paper_svc.get_by_name(paper_name)

        # Paper doesn't exist - offer to create it
        if target_paper is None:
            print_warning(f'Paper "{paper_name}" not found')
            console.print()
            if typer.confirm(f'Would you like to create paper "{paper_name}" first?'):
                paper_deadline = typer.prompt('Paper deadline (e.g., 3/31, "in 4 weeks")')

                # Ask about PDF
                new_pdf_path: Optional[str] = None
                if typer.confirm('Do you have a PDF draft to link?'):
                    pdf_input = typer.prompt('Enter PDF path')
                    path = Path(pdf_input).expanduser().resolve()
                    if path.exists() and path.suffix.lower() == '.pdf':
                        new_pdf_path = str(path)
                    else:
                        print_warning(f'PDF not found: {pdf_input}')

                try:
                    deadline_date = parse_date(paper_deadline)
                    target_paper = paper_svc.create(
                        name=paper_name,
                        deadline=deadline_date,
                        pdf_path=new_pdf_path,
                    )
                    print_success(f'Created paper "{target_paper.name}"')
                except ValueError as e:
                    print_error(f'Failed to create paper: {e}')
                    raise typer.Exit(1)
            else:
                print_info('Milestone not created. Create the paper first.')
                raise typer.Exit(0)

        # Now create the milestone
        milestone_service = MilestoneService()
        try:
            due = parse_date(due_date)

            # Determine start_date based on existing milestones
            existing_milestones = milestone_service.list_by_paper(target_paper.id)
            if existing_milestones:
                # Find the latest due_date among existing milestones that's before this one
                earlier_milestones = [m for m in existing_milestones if m.due_date < due]
                if earlier_milestones:
                    start_date = max(m.due_date for m in earlier_milestones)
                else:
                    start_date = date.today()
            else:
                start_date = date.today()

            milestone = milestone_service.create(
                paper_id=target_paper.id,
                description=description,
                start_date=start_date,
                due_date=due,
            )
            print_success(f'Created milestone for "{target_paper.name}"')
            typer.echo(f'  Description: {milestone.description}')
            typer.echo(f'  Period: {format_date(start_date)} → {format_date(due)}')

            # Auto-decompose milestone into tasks
            try:
                decomposition_service = DecompositionService()
                with console.status('Generating daily tasks...'):
                    tasks = decomposition_service.decompose_milestone(milestone.id)
                print_success(f'Generated {len(tasks)} daily tasks')
            except ValueError as e:
                print_warning(f'Could not auto-generate tasks: {e}')

        except ValueError as e:
            print_error(str(e))
            raise typer.Exit(1)

    elif command == 'add_milestones':
        # Handle multiple milestones at once
        paper_name = params.get('paper_name')
        milestones_list = params.get('milestones', [])

        if not paper_name or not milestones_list:
            print_error('Could not extract paper name and milestones from input')
            raise typer.Exit(1)

        paper_svc = PaperService()
        target_paper = paper_svc.get_by_name(paper_name)

        # Paper doesn't exist - offer to create it
        if target_paper is None:
            print_warning(f'Paper "{paper_name}" not found')
            console.print()
            if typer.confirm(f'Would you like to create paper "{paper_name}" first?'):
                paper_deadline = typer.prompt('Paper deadline (e.g., 3/31, "in 4 weeks")')

                # Ask about PDF
                new_pdf_path: Optional[str] = None
                if typer.confirm('Do you have a PDF draft to link?'):
                    pdf_input = typer.prompt('Enter PDF path')
                    path = Path(pdf_input).expanduser().resolve()
                    if path.exists() and path.suffix.lower() == '.pdf':
                        new_pdf_path = str(path)
                    else:
                        print_warning(f'PDF not found: {pdf_input}')

                try:
                    deadline_date = parse_date(paper_deadline)
                    target_paper = paper_svc.create(
                        name=paper_name,
                        deadline=deadline_date,
                        pdf_path=new_pdf_path,
                    )
                    print_success(f'Created paper "{target_paper.name}"')
                except ValueError as e:
                    print_error(f'Failed to create paper: {e}')
                    raise typer.Exit(1)
            else:
                print_info('Milestones not created. Create the paper first.')
                raise typer.Exit(0)

        # Now create all milestones
        milestone_service = MilestoneService()
        created_milestones = []
        total_tasks = 0

        # Parse all milestones and sort by due_date
        parsed_milestones = []
        for ms in milestones_list:
            description = ms.get('description')
            due_date_str = ms.get('due_date')

            if not description or not due_date_str:
                print_warning(f'Skipping incomplete milestone: {ms}')
                continue

            try:
                due = parse_date(due_date_str)
                parsed_milestones.append({'description': description, 'due_date': due})
            except ValueError as e:
                print_error(f'Failed to parse date for "{description}": {e}')

        # Sort milestones by due_date to ensure sequential ordering
        parsed_milestones.sort(key=lambda x: x['due_date'])

        # Create milestones with proper start_date (sequential)
        prev_due_date = date.today()
        for ms in parsed_milestones:
            description = ms['description']
            due = ms['due_date']

            try:
                milestone = milestone_service.create(
                    paper_id=target_paper.id,
                    description=description,
                    start_date=prev_due_date,
                    due_date=due,
                )
                created_milestones.append(milestone)
                print_success(f'Created milestone for "{target_paper.name}"')
                typer.echo(f'  Description: {milestone.description}')
                typer.echo(f'  Period: {format_date(prev_due_date)} → {format_date(due)}')

                # Update prev_due_date for next milestone
                prev_due_date = due

                # Auto-decompose milestone into tasks
                try:
                    decomposition_service = DecompositionService()
                    with console.status(f'Generating tasks for "{description}"...'):
                        tasks = decomposition_service.decompose_milestone(milestone.id)
                    print_success(f'Generated {len(tasks)} daily tasks')
                    total_tasks += len(tasks)
                except ValueError as e:
                    print_warning(f'Could not auto-generate tasks: {e}')

            except ValueError as e:
                print_error(f'Failed to create milestone "{description}": {e}')

        if created_milestones:
            console.print()
            print_success(f'Created {len(created_milestones)} milestone(s) with {total_tasks} total tasks')
        else:
            print_error('No milestones were created')
            raise typer.Exit(1)

        if not target_paper.pdf_path:
            print_info('Tip: Link a PDF for more detailed, context-aware task generation')

    elif command == 'update_paper':
        name = params.get('name')
        pdf_path = params.get('pdf_path')
        new_deadline = params.get('deadline')
        new_name = params.get('new_name')

        if not name:
            print_error('Could not extract paper name from input')
            raise typer.Exit(1)

        paper_svc = PaperService()
        target_paper = paper_svc.get_by_name(name)

        if target_paper is None:
            print_error(f'Paper "{name}" not found')
            print_info('Use "paper-bartender list papers" to see existing papers')
            raise typer.Exit(1)

        updated = False
        old_name = target_paper.name

        # Update name if provided
        if new_name:
            # Check if new name already exists
            existing = paper_svc.get_by_name(new_name)
            if existing and existing.id != target_paper.id:
                print_error(f'Paper "{new_name}" already exists')
                raise typer.Exit(1)
            target_paper.name = new_name
            updated = True
            print_success(f'Renamed paper "{old_name}" → "{new_name}"')

        # Update PDF path if provided
        if pdf_path:
            path = Path(pdf_path).expanduser().resolve()
            if path.exists() and path.suffix.lower() == '.pdf':
                target_paper.pdf_path = str(path)
                updated = True
                print_success(f'Updated PDF path for "{target_paper.name}"')
                typer.echo(f'  PDF: {path}')
            else:
                print_error(f'PDF not found or invalid: {pdf_path}')
                raise typer.Exit(1)

        # Update deadline if provided
        if new_deadline:
            try:
                deadline_date = parse_date(new_deadline)
                target_paper.deadline = deadline_date
                updated = True
                print_success(f'Updated deadline for "{target_paper.name}"')
                typer.echo(f'  Deadline: {format_date(deadline_date)}')
            except ValueError as e:
                print_error(f'Invalid deadline: {e}')
                raise typer.Exit(1)

        if updated:
            paper_svc.update(target_paper)
        else:
            print_warning('No updates were made')

    else:
        print_error(f'Could not understand: "{text}"')
        print_info('Try something like:')
        typer.echo('  paper-bartender do "add paper MyPaper deadline March 15"')
        typer.echo('  paper-bartender do "milestone for MyPaper: write intro by Feb 10"')
        typer.echo('  paper-bartender do "add pdf ~/paper.pdf to MyPaper"')
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
