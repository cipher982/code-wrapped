"""Tests for session parsers."""

import pytest
from pathlib import Path
from datetime import datetime, timezone

from code_wrapped.parsers.base import (
    extract_repo_from_path,
    sanitize_prompt,
    parse_iso_timestamp,
)
from code_wrapped.parsers.claude import parse_claude_sessions
from code_wrapped.parsers.codex import parse_codex_sessions


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestExtractRepoFromPath:
    """Tests for extract_repo_from_path function."""

    def test_simple_git_path(self):
        assert extract_repo_from_path("/Users/dave/git/my-project") == "my-project"

    def test_nested_git_path(self):
        """Nested paths should return full path after git directory."""
        assert extract_repo_from_path("/Users/dave/git/work/secret-repo") == "work/secret-repo"
        assert extract_repo_from_path("/Users/dave/git/me/mytech") == "me/mytech"

    def test_home_directory(self):
        """Home directory should return ~."""
        import os
        home = os.path.expanduser("~")
        assert extract_repo_from_path(home) == "~"

    def test_no_git_fallback(self):
        """Without git in path, return last directory name."""
        assert extract_repo_from_path("/some/random/path/project") == "project"

    def test_none_input(self):
        assert extract_repo_from_path(None) is None

    def test_empty_string(self):
        assert extract_repo_from_path("") is None


class TestSanitizePrompt:
    """Tests for sanitize_prompt function."""

    def test_truncates_long_prompts(self):
        long_prompt = "a" * 300
        result = sanitize_prompt(long_prompt)
        assert len(result) <= 203  # 200 + "..."

    def test_redacts_openai_keys(self):
        prompt = "Use key sk-abc123xyz456789012345678901234567890"
        result = sanitize_prompt(prompt)
        assert "sk-abc" not in result
        assert "[REDACTED]" in result

    def test_redacts_anthropic_keys(self):
        prompt = "Use key sk-ant-api03-abc123xyz456789012345"
        result = sanitize_prompt(prompt)
        assert "sk-ant" not in result

    def test_redacts_paths(self):
        prompt = "Read /Users/dave/git/project/secrets.txt"
        result = sanitize_prompt(prompt)
        assert "/Users/dave" not in result


class TestParseIsoTimestamp:
    """Tests for parse_iso_timestamp function."""

    def test_parses_z_suffix(self):
        result = parse_iso_timestamp("2025-06-15T14:00:00.000Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6

    def test_parses_timezone_offset(self):
        result = parse_iso_timestamp("2025-06-15T14:00:00+00:00")
        assert result is not None

    def test_none_input(self):
        assert parse_iso_timestamp(None) is None

    def test_invalid_format(self):
        assert parse_iso_timestamp("not a date") is None


class TestClaudeParser:
    """Tests for Claude session parser."""

    def test_parses_fixture(self):
        sessions = list(parse_claude_sessions(FIXTURES_DIR / "claude"))
        assert len(sessions) == 1

        session = sessions[0]
        assert session.id == "test-session-1"
        assert session.repo == "my-project"
        assert session.turn_count == 4
        assert session.tools_used.get("Bash") == 1
        assert session.branch == "main"


class TestCodexParser:
    """Tests for Codex session parser."""

    def test_parses_old_format_fixture(self):
        sessions = list(parse_codex_sessions(FIXTURES_DIR / "codex"))
        assert len(sessions) == 1

        session = sessions[0]
        assert session.id == "codex-test-session-1"
        assert session.repo == "another-project"
        assert session.turn_count == 4  # 4 items
        assert session.tools_used.get("shell") == 1
