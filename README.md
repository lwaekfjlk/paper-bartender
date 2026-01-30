# Paper Bartender

A CLI tool to help researchers manage paper deadlines by decomposing milestones into daily tasks using AI.

[![PyPI version](https://badge.fury.io/py/paper-bartender.svg)](https://pypi.org/project/paper-bartender/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Features

- Track multiple papers with deadlines and conference information
- Create milestones for each paper
- Automatically decompose milestones into actionable daily tasks using Claude or GPT-4
- View today's tasks at a glance
- Track overdue and pending tasks

## Installation

### Install from PyPI (Recommended)

```bash
# Using pip
pip install paper-bartender

# Or using pipx (recommended for CLI tools)
pipx install paper-bartender
```

### Install from Source

```bash
# Clone the repository
git clone https://github.com/lwaekfjlk/paper-bartender.git
cd paper-bartender

# Install with pip
pip install .

# Or install with poetry (for development)
poetry install
```

### Verify Installation

```bash
paper-bartender --help
```

## Configuration

Set your API key as an environment variable:

```bash
# For Anthropic Claude (recommended)
export PAPER_BARTENDER_ANTHROPIC_API_KEY="your-anthropic-key"

# Or for OpenAI
export PAPER_BARTENDER_OPENAI_API_KEY="your-openai-key"
```

Optional configuration:

```bash
# Explicitly choose provider (auto-detects by default)
export PAPER_BARTENDER_LLM_PROVIDER="anthropic"  # or "openai"

# Change models
export PAPER_BARTENDER_CLAUDE_MODEL="claude-sonnet-4-20250514"
export PAPER_BARTENDER_OPENAI_MODEL="gpt-4o"

# Change data directory (default: ~/.paper-bartender)
export PAPER_BARTENDER_DATA_DIR="/path/to/data"
```

## Usage

### Show Today's Tasks

```bash
# Show today's tasks (default command)
paper-bartender

# Show all pending tasks
paper-bartender today --all

# Filter by paper
paper-bartender today --paper "My Paper"
```

### Add a Paper

```bash
paper-bartender add paper "My Research Paper" --deadline 2025-05-15 --conference NeurIPS
```

Date formats supported:
- ISO format: `2025-05-15`
- Short format: `5/15`
- Relative: `in 2 weeks`, `in 10 days`, `tomorrow`

### Add a Milestone

```bash
paper-bartender add milestone "My Research Paper" "Write introduction" --due 5/10

# With priority (1-5, higher = more important)
paper-bartender add milestone "My Research Paper" "Run experiments" --due 5/5 --priority 3
```

### List Papers and Milestones

```bash
# List all papers
paper-bartender list papers

# Include archived papers
paper-bartender list papers --archived

# List milestones for a paper
paper-bartender list milestones "My Research Paper"

# Include completed milestones
paper-bartender list milestones "My Research Paper" --completed
```

### Decompose Milestones into Tasks

```bash
# Generate daily tasks for all pending milestones
paper-bartender decompose "My Research Paper"

# Preview without saving (dry run)
paper-bartender decompose "My Research Paper" --dry-run

# Re-decompose already decomposed milestones
paper-bartender decompose "My Research Paper" --force
```

## Example Workflow

```bash
# 1. Add a paper with deadline
paper-bartender add paper "Awesome ML Paper" --deadline 2025-06-01 --conference ICML

# 2. Add milestones
paper-bartender add milestone "Awesome ML Paper" "Complete literature review" --due 5/10
paper-bartender add milestone "Awesome ML Paper" "Finish experiments" --due 5/20
paper-bartender add milestone "Awesome ML Paper" "Write first draft" --due 5/28

# 3. Generate daily tasks
paper-bartender decompose "Awesome ML Paper"

# 4. Check today's tasks every day
paper-bartender
```

## Data Storage

All data is stored locally in JSON format at `~/.paper-bartender/data.json`. Backups are automatically created before destructive operations.

## Commands Reference

| Command | Description |
|---------|-------------|
| `paper-bartender` | Show today's tasks |
| `paper-bartender today [--all] [--paper NAME]` | Show today's or all pending tasks |
| `paper-bartender add paper NAME --deadline DATE [--conference NAME]` | Add a new paper |
| `paper-bartender add milestone PAPER DESC --due DATE [--priority N]` | Add a milestone |
| `paper-bartender list papers [--archived]` | List all papers |
| `paper-bartender list milestones PAPER [--completed]` | List milestones for a paper |
| `paper-bartender decompose PAPER [--force] [--dry-run]` | Generate tasks from milestones |

## Development

```bash
# Install dev dependencies
poetry install

# Run tests
pytest

# Type checking
mypy --strict paper_bartender

# Format code
ruff format .
ruff check --fix .
```

## Publishing to PyPI

To publish a new version:

```bash
# Update version in pyproject.toml and paper_bartender/__init__.py

# Build the package
poetry build

# Publish to PyPI (requires PyPI credentials)
poetry publish

# Or publish to TestPyPI first
poetry publish -r testpypi
```

## License

Apache 2.0 License
