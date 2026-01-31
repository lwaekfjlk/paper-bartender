"""Decomposition service using LLM APIs (Anthropic Claude or OpenAI)."""

import json
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from paper_bartender.config.settings import LLMProvider, Settings, get_settings
from paper_bartender.models.milestone import Milestone
from paper_bartender.models.paper import Paper
from paper_bartender.models.task import Task
from paper_bartender.services.milestone_service import MilestoneService
from paper_bartender.services.paper_service import PaperService
from paper_bartender.services.task_service import TaskService
from paper_bartender.storage.json_store import JsonStore


class DecompositionService:
    """Service for decomposing milestones into daily tasks using LLM."""

    def __init__(
        self,
        store: Optional[JsonStore] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        """Initialize the decomposition service."""
        self._store = store or JsonStore()
        self._settings = settings or get_settings()
        self._paper_service = PaperService(self._store)
        self._milestone_service = MilestoneService(self._store)
        self._task_service = TaskService(self._store)

    def _get_available_days(self, start_date: date, end_date: date) -> List[date]:
        """Get list of available days between start and end date."""
        days = []
        current = start_date
        while current <= end_date:
            days.append(current)
            current += timedelta(days=1)
        return days

    def _create_simple_tasks(
        self,
        milestone: Milestone,
        paper: Paper,
        available_days: List[date],
    ) -> List[Task]:
        """Create simple percentage-based tasks without PDF context.

        This is used when no PDF is linked to the paper.
        Creates 2-4 evenly distributed checkpoint tasks.
        """
        num_days = len(available_days)

        # Create one checkpoint per day for consistent daily progress tracking
        num_checkpoints = num_days

        tasks = []
        for i in range(num_checkpoints):
            # Calculate percentage (evenly distributed to reach 100%)
            percentage = int((i + 1) * 100 / num_checkpoints)

            # Calculate which day to schedule this task (spread from first to last day)
            if num_checkpoints == 1:
                day_index = 0  # Only one checkpoint, schedule on first day
            else:
                day_index = int(i * (num_days - 1) / (num_checkpoints - 1))
            scheduled_date = available_days[min(day_index, num_days - 1)]

            # Create task description
            description = f"[{percentage}% of '{milestone.description}']"

            task = Task(
                milestone_id=milestone.id,
                paper_id=paper.id,
                description=description,
                scheduled_date=scheduled_date,
                estimated_hours=self._settings.default_task_hours,
            )
            tasks.append(task)

        return tasks

    def _get_pdf_context(self, paper: Paper) -> Optional[str]:
        """Get context from the paper's PDF if available."""
        if not paper.pdf_path:
            return None

        try:
            from paper_bartender.utils.pdf import analyze_paper_sections, get_pdf_summary

            sections = analyze_paper_sections(paper.pdf_path)
            summary = get_pdf_summary(paper.pdf_path, max_chars=6000)

            # Build context about current paper status
            completed_sections = [s.replace('_', ' ') for s, v in sections.items() if v]
            missing_sections = [s.replace('_', ' ') for s, v in sections.items() if not v]

            context = f"""
CURRENT PAPER CONTENT (from PDF):
Completed sections: {', '.join(completed_sections) if completed_sections else 'None detected'}
Missing/incomplete sections: {', '.join(missing_sections) if missing_sections else 'None detected'}

Paper excerpt:
{summary}
"""
            return context
        except Exception:
            return None

    def _build_prompt(
        self,
        paper: Paper,
        milestone: Milestone,
        available_days: List[date],
        pdf_context: Optional[str] = None,
    ) -> str:
        """Build the prompt for the LLM."""
        days_str = ', '.join(d.strftime('%Y-%m-%d') for d in available_days[:14])
        if len(available_days) > 14:
            days_str += f' ... ({len(available_days)} days total)'

        # Base prompt
        prompt = f"""You are helping a researcher plan tasks for their paper milestone.

PAPER: {paper.name}
DEADLINE: {paper.deadline.strftime('%Y-%m-%d')}
"""

        # Add PDF context if available
        if pdf_context:
            prompt += f"""
{pdf_context}
"""

        prompt += f"""
MILESTONE TO COMPLETE:
- Description: "{milestone.description}"
- Due Date: {milestone.due_date.strftime('%Y-%m-%d')}

AVAILABLE DAYS: {days_str}
TOTAL DAYS AVAILABLE: {len(available_days)}

Create 2-4 daily tasks that represent PROGRESS CHECKPOINTS toward completing the "{milestone.description}" milestone.

IMPORTANT GUIDELINES:
1. Each task MUST include the milestone name in the format: "[X% of '{milestone.description}']"
2. Tasks should be evenly distributed to reach 100% by the due date
3. After the percentage, provide CONCRETE and SPECIFIC suggestions:
   - What exactly should be done at this checkpoint
   - What deliverables or outputs are expected
   - How to verify this progress has been achieved
"""

        if pdf_context:
            prompt += """4. Since a PDF is provided, reference the paper's current state:
   - Mention specific sections, figures, or tables that need work
   - Reference actual content from the paper when relevant
"""
        else:
            prompt += """4. Give actionable, specific tasks even without PDF context
"""

        prompt += f"""
Return ONLY a JSON array with objects containing:
- "scheduled_date": date in YYYY-MM-DD format
- "description": task with format "[X% of '{milestone.description}'] Concrete action..."
- "estimated_hours": estimated hours (2-4)

Example for milestone "rerun experiments":
[
  {{"scheduled_date": "2025-02-01", "description": "[25% of 'rerun experiments'] Set up experiment environment and verify all dependencies. Checkpoint: environment runs without errors", "estimated_hours": 2}},
  {{"scheduled_date": "2025-02-02", "description": "[50% of 'rerun experiments'] Execute baseline experiments and log all outputs. Checkpoint: baseline results match expected ranges", "estimated_hours": 3}},
  {{"scheduled_date": "2025-02-03", "description": "[75% of 'rerun experiments'] Run full experiment suite and collect metrics. Checkpoint: all experiments complete with recorded metrics", "estimated_hours": 3}},
  {{"scheduled_date": "2025-02-04", "description": "[100% of 'rerun experiments'] Compare results with paper claims and document any discrepancies. Checkpoint: results summary ready for paper update", "estimated_hours": 2}}
]

Return ONLY the JSON array, no other text."""

        return prompt

    def _parse_response(
        self,
        response_text: str,
        milestone: Milestone,
        paper: Paper,
    ) -> List[Task]:
        """Parse LLM response into Task objects."""
        # Extract JSON from response
        text = response_text.strip()
        if text.startswith('```'):
            # Remove markdown code blocks
            lines = text.split('\n')
            text = '\n'.join(
                line for line in lines
                if not line.startswith('```')
            )

        try:
            task_data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f'Failed to parse LLM response as JSON: {e}') from e

        tasks = []
        for item in task_data:
            scheduled_date = date.fromisoformat(item['scheduled_date'])
            task = Task(
                milestone_id=milestone.id,
                paper_id=paper.id,
                description=item['description'],
                scheduled_date=scheduled_date,
                estimated_hours=item.get('estimated_hours', self._settings.default_task_hours),
            )
            tasks.append(task)

        return tasks

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)
        message = client.messages.create(
            model=self._settings.claude_model,
            max_tokens=4096,
            messages=[
                {'role': 'user', 'content': prompt}
            ],
        )

        content_block = message.content[0]
        if not hasattr(content_block, 'text'):
            raise ValueError('Unexpected response type from Anthropic API')
        return str(content_block.text)

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        import openai

        client = openai.OpenAI(api_key=self._settings.openai_api_key)
        response = client.chat.completions.create(
            model=self._settings.openai_model,
            max_tokens=4096,
            messages=[
                {'role': 'user', 'content': prompt}
            ],
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError('Empty response from OpenAI API')
        return content

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider."""
        provider = self._settings.get_provider()

        if provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(prompt)
        elif provider == LLMProvider.OPENAI:
            return self._call_openai(prompt)
        else:
            raise ValueError(f'Unknown LLM provider: {provider}')

    def decompose_milestone(
        self,
        milestone_id: UUID,
        force: bool = False,
        dry_run: bool = False,
    ) -> List[Task]:
        """Decompose a milestone into daily tasks.

        Args:
            milestone_id: ID of the milestone to decompose.
            force: If True, re-decompose even if already decomposed.
            dry_run: If True, return tasks without saving.

        Returns:
            List of generated tasks.

        Raises:
            ValueError: If milestone not found or API key not configured.
        """
        milestone = self._milestone_service.get_by_id(milestone_id)
        if milestone is None:
            raise ValueError(f'Milestone with id {milestone_id} not found')

        if milestone.decomposed and not force:
            raise ValueError(
                f'Milestone "{milestone.description}" has already been decomposed. '
                'Use --force to re-decompose.'
            )

        paper = self._paper_service.get_by_id(milestone.paper_id)
        if paper is None:
            raise ValueError('Paper for milestone not found')

        # Calculate available days
        today = date.today()
        # Use milestone's start_date if set, otherwise use today
        if milestone.start_date and milestone.start_date >= today:
            start_date = milestone.start_date
        elif milestone.start_date and milestone.start_date < today:
            # If start_date is in the past, use today
            start_date = today
        else:
            start_date = today if today < milestone.due_date else milestone.due_date - timedelta(days=7)
        available_days = self._get_available_days(start_date, milestone.due_date)

        if not available_days:
            raise ValueError('No available days for scheduling tasks')

        # Check if PDF is available for detailed decomposition
        pdf_context = None
        if paper.pdf_path:
            pdf_context = self._get_pdf_context(paper)

        if pdf_context:
            # Full LLM-based decomposition with PDF context
            prompt = self._build_prompt(paper, milestone, available_days, pdf_context)
            response_text = self._call_llm(prompt)
            tasks = self._parse_response(response_text, milestone, paper)
        else:
            # Simple percentage-based decomposition without PDF
            tasks = self._create_simple_tasks(milestone, paper, available_days)

        if not dry_run:
            # Delete existing tasks if force re-decomposing
            if force and milestone.decomposed:
                self._task_service.delete_by_milestone(milestone_id)

            # Save new tasks
            self._task_service.create_bulk(tasks)

            # Mark milestone as decomposed
            self._milestone_service.mark_decomposed(milestone_id)

        return tasks

    def decompose_paper(
        self,
        paper_id: UUID,
        force: bool = False,
        dry_run: bool = False,
    ) -> List[Task]:
        """Decompose all pending milestones for a paper.

        Args:
            paper_id: ID of the paper.
            force: If True, re-decompose even if already decomposed.
            dry_run: If True, return tasks without saving.

        Returns:
            List of all generated tasks.
        """
        paper = self._paper_service.get_by_id(paper_id)
        if paper is None:
            raise ValueError(f'Paper with id {paper_id} not found')

        if force:
            milestones = self._milestone_service.list_by_paper(paper_id, include_completed=False)
        else:
            milestones = self._milestone_service.list_not_decomposed(paper_id)

        if not milestones:
            return []

        all_tasks: List[Task] = []
        for milestone in milestones:
            tasks = self.decompose_milestone(milestone.id, force=force, dry_run=dry_run)
            all_tasks.extend(tasks)

        return all_tasks
