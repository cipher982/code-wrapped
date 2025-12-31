"""Base session model and utilities shared across parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal, Optional


class AgentType(str, Enum):
    """Supported AI coding agents."""

    CLAUDE = "claude"
    CODEX = "codex"
    CURSOR = "cursor"
    GEMINI = "gemini"


@dataclass
class Session:
    """Unified session model across all agents.

    This is the canonical data structure that all agent parsers
    must produce. Enables cross-agent comparison and analysis.
    """

    # Identity
    id: str
    agent: AgentType

    # Timing
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: float = 0.0

    # Context
    repo: Optional[str] = None
    branch: Optional[str] = None

    # Metrics
    turn_count: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0
    token_count: Optional[int] = None

    # Tool Usage (Claude/Codex specific)
    tools_used: dict[str, int] = field(default_factory=dict)

    # Content (for analysis - redacted/sanitized)
    user_prompts: list[str] = field(default_factory=list)

    # Enriched (computed later)
    topic: Optional[str] = None
    vibe: Optional[str] = None
    prompt_archetype: Optional[str] = None

    # Errors encountered (for "Error of the Year")
    errors: list[str] = field(default_factory=list)

    # Parse tracking
    _parse_errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Compute derived fields."""
        if self.ended_at and self.started_at:
            delta = self.ended_at - self.started_at
            self.duration_minutes = delta.total_seconds() / 60

    @property
    def hour_of_day(self) -> int:
        """Return the hour (0-23) when session started."""
        return self.started_at.hour

    @property
    def day_of_week(self) -> int:
        """Return day of week (0=Monday, 6=Sunday)."""
        return self.started_at.weekday()

    @property
    def date_str(self) -> str:
        """Return date as YYYY-MM-DD string."""
        return self.started_at.strftime("%Y-%m-%d")


def extract_repo_from_path(cwd: str | None) -> str | None:
    """Extract sanitized repo name from working directory path.

    Privacy: Only returns the repo name, not the full path.

    Examples:
        /Users/dave/git/my-project -> my-project
        /Users/dave/git/work/secret-repo -> secret-repo
        /home/user/projects/foo -> foo
    """
    if not cwd:
        return None

    path = Path(cwd)

    # Home directory
    if path == Path.home():
        return "~"

    # Check common git directory patterns
    parts = path.parts
    for git_dir in ("git", "projects", "repos", "src", "code"):
        if git_dir in parts:
            idx = parts.index(git_dir)
            if idx + 1 < len(parts):
                return parts[idx + 1]

    # Fallback: use last directory name
    return path.name if path.name else None


def sanitize_prompt(prompt: str, max_length: int = 200) -> str:
    """Sanitize a user prompt for safe storage/analysis.

    - Truncates to max_length
    - Removes potential secrets (API keys, passwords)
    - Removes file paths beyond repo name
    """
    if not prompt:
        return ""

    # Truncate
    if len(prompt) > max_length:
        prompt = prompt[:max_length] + "..."

    # Remove common secret patterns
    secret_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI keys
        r"sk-ant-[a-zA-Z0-9-]{20,}",  # Anthropic keys
        r"ghp_[a-zA-Z0-9]{36}",  # GitHub tokens
        r"password[=:]\s*\S+",  # Passwords
        r"api[_-]?key[=:]\s*\S+",  # API keys
    ]

    for pattern in secret_patterns:
        prompt = re.sub(pattern, "[REDACTED]", prompt, flags=re.IGNORECASE)

    # Remove full paths, keep just filenames
    prompt = re.sub(r"/Users/[^/]+/[^\s]+/([^/\s]+)", r"\1", prompt)
    prompt = re.sub(r"/home/[^/]+/[^\s]+/([^/\s]+)", r"\1", prompt)

    return prompt


def parse_iso_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO8601 timestamp string to datetime."""
    if not ts:
        return None

    try:
        # Handle Z suffix
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
