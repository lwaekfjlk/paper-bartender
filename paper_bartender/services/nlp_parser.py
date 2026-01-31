"""Natural language parser service using LLM."""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from paper_bartender.config.settings import LLMProvider, Settings, get_settings


class NLPParserService:
    """Service for parsing natural language commands using LLM."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize the NLP parser service."""
        self._settings = settings or get_settings()

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)
        message = client.messages.create(
            model=self._settings.claude_model,
            max_tokens=1024,
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
            max_tokens=1024,
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

    def parse(self, user_input: str) -> Dict[str, Any]:
        """Parse natural language input into structured command.

        Args:
            user_input: Natural language input from user.

        Returns:
            Dictionary with command type and parameters.
        """
        today = date.today()
        prompt = f"""Parse the following user input into a structured command for a paper management CLI.

TODAY'S DATE: {today.strftime('%Y-%m-%d')}

USER INPUT: "{user_input}"

Available commands:
1. add_paper: Add a new paper with name, deadline, and optional pdf_path (NO milestones mentioned)
2. add_paper_with_milestones: Add a NEW paper AND its milestones together. Use when user wants to create a paper that doesn't exist yet AND add milestones in the same command.
3. add_milestone: Add a milestone to an EXISTING paper with paper_name, description, and due_date
4. add_milestones: Add MULTIPLE milestones to an EXISTING paper at once.
5. update_paper: Update an existing paper's properties (like pdf_path, deadline, name/rename)
6. unknown: If the input doesn't match any command

Parse the input and return ONLY a JSON object with:
- "command": one of "add_paper", "add_paper_with_milestones", "add_milestone", "add_milestones", "update_paper", "unknown"
- "params": object with the relevant parameters

For dates, convert relative dates (like "next Friday", "in 2 weeks", "Feb 15") to YYYY-MM-DD format.

Examples:
- "add paper ML Research due March 15" -> {{"command": "add_paper", "params": {{"name": "ML Research", "deadline": "2026-03-15"}}}}
- "new milestone for ML Research: finish experiments by Feb 10" -> {{"command": "add_milestone", "params": {{"paper_name": "ML Research", "description": "finish experiments", "due_date": "2026-02-10"}}}}
- "paper ABC deadline 2/20 pdf ~/paper.pdf" -> {{"command": "add_paper", "params": {{"name": "ABC", "deadline": "2026-02-20", "pdf_path": "~/paper.pdf"}}}}
- "add pdf ~/docs/paper.pdf to SWM" -> {{"command": "update_paper", "params": {{"name": "SWM", "pdf_path": "~/docs/paper.pdf"}}}}
- "rename SWM to ABC" -> {{"command": "update_paper", "params": {{"name": "SWM", "new_name": "ABC"}}}}
- "change paper name from OldName to NewName" -> {{"command": "update_paper", "params": {{"name": "OldName", "new_name": "NewName"}}}}
- "for SWM paper: fix bugs by 2/4, run experiments by 2/10, rewrite results by 2/15" -> {{"command": "add_milestones", "params": {{"paper_name": "SWM", "milestones": [{{"description": "fix bugs", "due_date": "2026-02-04"}}, {{"description": "run experiments", "due_date": "2026-02-10"}}, {{"description": "rewrite results", "due_date": "2026-02-15"}}]}}}}
- "add SWM paper deadline 2/15, milestone1: fix bug by 2/7, milestone2: run experiments by 2/14" -> {{"command": "add_paper_with_milestones", "params": {{"name": "SWM", "deadline": "2026-02-15", "milestones": [{{"description": "fix bug", "due_date": "2026-02-07"}}, {{"description": "run experiments", "due_date": "2026-02-14"}}]}}}}
- "create paper ABC due 3/1 with milestones: write intro by 2/10, finish experiments by 2/20" -> {{"command": "add_paper_with_milestones", "params": {{"name": "ABC", "deadline": "2026-03-01", "milestones": [{{"description": "write intro", "due_date": "2026-02-10"}}, {{"description": "finish experiments", "due_date": "2026-02-20"}}]}}}}

Return ONLY the JSON object, no other text."""

        response_text = self._call_llm(prompt).strip()

        # Extract JSON from response
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(
                line for line in lines
                if not line.startswith('```')
            )

        try:
            result: Dict[str, Any] = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f'Failed to parse LLM response: {e}') from e

        return result
