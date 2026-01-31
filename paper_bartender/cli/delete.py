"""Delete commands for paper-bartender CLI."""

import typer

from paper_bartender.services.milestone_service import MilestoneService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.utils.display import print_error, print_success, print_warning

delete_app = typer.Typer(help='Delete papers and milestones')


@delete_app.command('paper')
def delete_paper(
    name: str = typer.Argument(..., help='Name of the paper to delete'),
    force: bool = typer.Option(
        False,
        '--force',
        '-f',
        help='Skip confirmation prompt',
    ),
) -> None:
    """Delete a paper and all its milestones and tasks."""
    paper_service = PaperService()
    paper = paper_service.get_by_name(name)

    if paper is None:
        print_error(f'Paper "{name}" not found')
        raise typer.Exit(1)

    if not force:
        # Get milestone count for warning
        milestone_service = MilestoneService()
        milestones = milestone_service.list_by_paper(paper.id)

        warning_msg = f'This will delete paper "{paper.name}"'
        if milestones:
            warning_msg += f' and {len(milestones)} milestone(s) with all associated tasks'
        warning_msg += '.'

        print_warning(warning_msg)
        confirm = typer.confirm('Are you sure?')
        if not confirm:
            typer.echo('Cancelled.')
            raise typer.Exit(0)

    if paper_service.delete(paper.id):
        print_success(f'Deleted paper "{paper.name}" and all associated data')
    else:
        print_error('Failed to delete paper')
        raise typer.Exit(1)


@delete_app.command('milestone')
def delete_milestone(
    paper_name: str = typer.Argument(..., help='Name of the paper'),
    description: str = typer.Argument(..., help='Description of the milestone to delete'),
    force: bool = typer.Option(
        False,
        '--force',
        '-f',
        help='Skip confirmation prompt',
    ),
) -> None:
    """Delete a milestone and all its tasks."""
    paper_service = PaperService()
    paper = paper_service.get_by_name(paper_name)

    if paper is None:
        print_error(f'Paper "{paper_name}" not found')
        raise typer.Exit(1)

    milestone_service = MilestoneService()
    milestones = milestone_service.list_by_paper(paper.id)

    # Find milestone by description (partial match)
    matching = [m for m in milestones if description.lower() in m.description.lower()]

    if not matching:
        print_error(f'No milestone matching "{description}" found')
        raise typer.Exit(1)

    if len(matching) > 1:
        print_warning(f'Multiple milestones match "{description}":')
        for m in matching:
            typer.echo(f'  - {m.description}')
        print_error('Please provide a more specific description')
        raise typer.Exit(1)

    milestone = matching[0]

    if not force:
        print_warning(f'This will delete milestone "{milestone.description}" and all its tasks.')
        confirm = typer.confirm('Are you sure?')
        if not confirm:
            typer.echo('Cancelled.')
            raise typer.Exit(0)

    if milestone_service.delete(milestone.id):
        print_success(f'Deleted milestone "{milestone.description}"')
    else:
        print_error('Failed to delete milestone')
        raise typer.Exit(1)
