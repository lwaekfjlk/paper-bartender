# Paper Bartender

A CLI tool to help researchers manage paper deadlines by decomposing milestones into daily tasks using AI.

[![PyPI version](https://badge.fury.io/py/paper-bartender.svg)](https://pypi.org/project/paper-bartender/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Features

- **Natural language interface** - Just tell it what you want in plain English
- Track multiple papers with deadlines
- Link papers to PDF files for context-aware task generation
- Create sequential milestones with automatic task decomposition
- AI reads your paper's PDF to generate tasks tailored to your current progress
- View today's tasks at a glance

## Installation

```bash
# Using pip
pip install paper-bartender

# Or using pipx (recommended for CLI tools)
pipx install paper-bartender
```

## Configuration

Set your API key:

```bash
# For Anthropic Claude (recommended)
export PAPER_BARTENDER_ANTHROPIC_API_KEY="your-anthropic-key"

# Or for OpenAI
export PAPER_BARTENDER_OPENAI_API_KEY="your-openai-key"
```

## Usage

### The `do` Command - Natural Language Interface

The easiest way to use Paper Bartender is with natural language:

```bash
# Add a paper with deadline
paper-bartender do "add paper ABC deadline Feb 20"

# Add a paper with PDF for smarter task generation
paper-bartender do "add paper ABC deadline Feb 20 pdf ~/papers/draft.pdf"

# Link a PDF to an existing paper
paper-bartender do "add pdf ~/Downloads/draft.pdf to ABC"

# Add a single milestone
paper-bartender do "milestone for ABC: finish experiments by Feb 10"

# Add multiple milestones at once (they become sequential!)
paper-bartender do "for ABC paper: fix pipeline bug by 2/4, rerun experiments by 2/10, rewrite results by 2/15"
```

When you add multiple milestones, they are automatically sequenced:
- **fix pipeline bug**: Today → 2/4
- **rerun experiments**: 2/4 → 2/10
- **rewrite results**: 2/10 → 2/15

### View Your Tasks

```bash
# Show today's tasks (default)
paper-bartender

# Show all upcoming progress
paper-bartender all

# Show timeline for a specific paper
paper-bartender timeline "ABC"

# Or filter any view by paper
paper-bartender today --paper "ABC"
paper-bartender all --paper "ABC"
```

### Mark Tasks Complete

```bash
# Mark a task as done (partial match)
paper-bartender done "fix pipeline"

# Skip a task
paper-bartender skip "review literature"
```

## Example Workflow

```bash
# 1. Add a paper with your PDF draft
paper-bartender do "add paper ICML Submission deadline Feb 20 pdf ~/papers/icml-draft.pdf"

# 2. Add all your milestones in one command
paper-bartender do "for ICML Submission: fix training bug by 2/4, run all experiments by 2/10, rewrite results section by 2/15, final polish by 2/19"

# 3. Check your tasks daily
paper-bartender

# 4. Mark tasks as done
paper-bartender done "identify bug"

# 5. See the full schedule
paper-bartender all
```

**Today's tasks with progress bars:**

```
📋 Today's Tasks (Sat, Jan 31)
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Paper            ┃ Checkpoint                                    ┃ Detailed Task                   ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ICML Submission  │ ███░░░░░░░░░  25% fix training bug            │ Review pipeline code and...     │
│ Other Paper      │ ██████░░░░░░  50% finish experiments          │ N/A                             │
└──────────────────┴───────────────────────────────────────────────┴─────────────────────────────────┘
```

**Timeline for a specific paper:**

```
$ paper-bartender timeline "ICML Submission"

📅 Upcoming Progress  (8 tasks across 5 days)

Today (1 task)
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Paper            ┃ Checkpoint                                    ┃ Detailed Task                   ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ICML Submission  │ ███░░░░░░░░░  25% fix training bug            │ Review pipeline code...         │
└──────────────────┴───────────────────────────────────────────────┴─────────────────────────────────┘

Tomorrow (1 task)
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Paper            ┃ Checkpoint                                    ┃ Detailed Task                   ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ICML Submission  │ ██████░░░░░░  50% fix training bug            │ Implement fixes...              │
└──────────────────┴───────────────────────────────────────────────┴─────────────────────────────────┘
```

---

## Advanced Commands

<details>
<summary><b>Add Paper (explicit command)</b></summary>

```bash
paper-bartender add paper "My Paper" --deadline 2025-05-15 --pdf ~/draft.pdf
```

Date formats: `2025-05-15`, `5/15`, `in 2 weeks`, `tomorrow`
</details>

<details>
<summary><b>Add Milestone (explicit command)</b></summary>

```bash
paper-bartender add milestone "My Paper" "Write intro" --due 5/10

# With priority (1-5)
paper-bartender add milestone "My Paper" "Experiments" --due 5/5 --priority 3

# Skip auto task generation
paper-bartender add milestone "My Paper" "Review" --due 5/8 --no-decompose
```
</details>

<details>
<summary><b>List Papers & Milestones</b></summary>

```bash
paper-bartender list papers
paper-bartender list papers --archived
paper-bartender list milestones "My Paper"
paper-bartender list milestones "My Paper" --completed
```
</details>

<details>
<summary><b>Re-generate Tasks</b></summary>

```bash
# Re-generate tasks (re-reads PDF for updated context)
paper-bartender decompose "My Paper" --force

# Preview without saving
paper-bartender decompose "My Paper" --dry-run
```
</details>

<details>
<summary><b>Delete Data</b></summary>

```bash
paper-bartender delete paper "My Paper"
paper-bartender delete milestone "My Paper" "Write intro"

# Clear everything (creates backup first)
paper-bartender clear

# Restore from backup
paper-bartender restore
```
</details>

## Commands Reference

| Command | Description |
|---------|-------------|
| `paper-bartender` | Show today's tasks |
| `paper-bartender all` | Show all upcoming tasks |
| `paper-bartender timeline "Paper"` | Show timeline for a specific paper |
| `paper-bartender do "..."` | **Natural language command** |
| `paper-bartender done "task"` | Mark task complete |
| `paper-bartender skip "task"` | Skip a task |
| `paper-bartender add paper ...` | Add paper (explicit) |
| `paper-bartender add milestone ...` | Add milestone (explicit) |
| `paper-bartender list papers` | List papers |
| `paper-bartender list milestones` | List milestones |
| `paper-bartender decompose` | Re-generate tasks |
| `paper-bartender delete` | Delete paper/milestone |
| `paper-bartender clear` | Clear all data |
| `paper-bartender restore` | Restore from backup |

## Data Storage

All data is stored locally at `~/.paper-bartender/data.json`. Backups are created automatically before destructive operations.

## Development

```bash
poetry install
pytest
mypy --strict paper_bartender
ruff format . && ruff check --fix .
```

## License

Apache 2.0 License
