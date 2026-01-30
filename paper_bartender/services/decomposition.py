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

    def _build_prompt(
        self,
        paper: Paper,
        milestone: Milestone,
        available_days: List[date],
    ) -> str:
        """Build the prompt for the LLM."""
        days_str = ', '.join(d.strftime('%Y-%m-%d') for d in available_days[:14])
        if len(available_days) > 14:
            days_str += f' ... ({len(available_days)} days total)'

        return f"""You are helping a researcher decompose a milestone into daily tasks.

Paper: {paper.name}
Paper Deadline: {paper.deadline.strftime('%Y-%m-%d')}
Conference: {paper.conference or 'Not specified'}

Milestone: {milestone.description}
Milestone Due Date: {milestone.due_date.strftime('%Y-%m-%d')}

Available days for scheduling tasks: {days_str}
Total available days: {len(available_days)}

Please decompose this milestone into specific, actionable daily tasks. Each task should:
- Be completable in 2-4 hours
- Be specific and actionable (not vague like "work on paper")
- Be scheduled on one of the available days
- Build logically on previous tasks

Return your response as a JSON array with objects containing:
- "scheduled_date": date in YYYY-MM-DD format
- "description": specific task description
- "estimated_hours": estimated hours (2-4)

Example format:
[
  {{"scheduled_date": "2025-02-01", "description": "Draft introduction section outline with 3 main points", "estimated_hours": 2}},
  {{"scheduled_date": "2025-02-02", "description": "Write first draft of related work section", "estimated_hours": 3}}
]

Return ONLY the JSON array, no other text."""

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
        start_date = today if today < milestone.due_date else milestone.due_date - timedelta(days=7)
        available_days = self._get_available_days(start_date, milestone.due_date)

        if not available_days:
            raise ValueError('No available days for scheduling tasks')

        # Build prompt and call LLM
        prompt = self._build_prompt(paper, milestone, available_days)
        response_text = self._call_llm(prompt)
        tasks = self._parse_response(response_text, milestone, paper)

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
