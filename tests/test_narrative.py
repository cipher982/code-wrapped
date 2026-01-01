"""Tests for narrative generation module."""

import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from code_wrapped.enrichment.awards import Award
from code_wrapped.narrative import compile_narrative_context, generate_insights
from code_wrapped.narrative.insights import _parse_narrative_response
from code_wrapped.narrative.story import NarrativeContext
from code_wrapped.parsers.base import AgentType, Session
from code_wrapped.stats import AgentStats, WrappedStats, aggregate_stats


# ===========================
# Fixtures - Mock Data
# ===========================


@pytest.fixture
def sample_sessions():
    """Create sample sessions for testing."""
    return [
        Session(
            id="session-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2025, 1, 15, 14, 30, tzinfo=timezone.utc),
            ended_at=datetime(2025, 1, 15, 15, 30, tzinfo=timezone.utc),
            duration_minutes=60.0,
            repo="test-repo",
            turn_count=30,
            user_message_count=15,
            assistant_message_count=15,
            token_count=100000,
            tools_used={"Bash": 10, "Edit": 5, "Read": 3},
            user_prompts=["Help me debug this API", "Fix the authentication"],
        ),
        Session(
            id="session-2",
            agent=AgentType.CODEX,
            started_at=datetime(2025, 2, 10, 2, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 2, 10, 6, 15, tzinfo=timezone.utc),
            duration_minutes=255.0,
            repo="big-project",
            turn_count=150,
            user_message_count=75,
            assistant_message_count=75,
            token_count=500000,
            tools_used={"Bash": 50, "Edit": 20, "Read": 10},
            user_prompts=["Refactor the entire auth system", "Add comprehensive tests"],
        ),
        Session(
            id="session-3",
            agent=AgentType.CLAUDE,
            started_at=datetime(2025, 3, 20, 14, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 3, 20, 14, 10, tzinfo=timezone.utc),
            duration_minutes=10.0,
            repo="test-repo",
            turn_count=8,
            user_message_count=4,
            assistant_message_count=4,
            token_count=20000,
            tools_used={"Bash": 2, "Edit": 1},
            user_prompts=["Quick fix for the bug"],
        ),
    ]


@pytest.fixture
def sample_stats(sample_sessions):
    """Generate stats from sample sessions."""
    return aggregate_stats(sample_sessions, 2025)


@pytest.fixture
def sample_awards():
    """Create sample awards."""
    return [
        Award(
            id="night_owl",
            name="Night Owl",
            emoji="🦉",
            description="Peak coding after midnight",
            detail="Your peak late-night hour: 2:00",
            value=10,
        ),
        Award(
            id="marathon_coder",
            name="Marathon Coder",
            emoji="🏃",
            description="Your longest session was epic",
            detail="Longest session: 4.2 hours on Claude",
            value=4.2,
        ),
    ]


# ===========================
# Tests - Story Context
# ===========================


def test_compile_narrative_context(sample_stats, sample_awards):
    """Test compilation of narrative context from stats."""
    context = compile_narrative_context(sample_stats, sample_awards)

    assert isinstance(context, NarrativeContext)
    assert context.year == 2025
    assert context.total_sessions == 3
    assert context.total_turns == 188
    assert context.award_count == 2
    assert "night_owl" in context.award_ids
    assert "marathon_coder" in context.award_ids


def test_narrative_context_agent_distribution(sample_stats, sample_awards):
    """Test agent distribution in narrative context."""
    context = compile_narrative_context(sample_stats, sample_awards)

    # Should detect Claude as primary (2/3 sessions)
    assert "claude" in context.primary_agent.lower()
    assert context.primary_agent_percentage > 50
    assert "claude" in context.agent_distribution
    assert "codex" in context.agent_distribution


def test_narrative_context_time_patterns(sample_stats, sample_awards):
    """Test time pattern detection in narrative context."""
    context = compile_narrative_context(sample_stats, sample_awards)

    # Peak hour should be detected
    assert context.peak_hour >= 0 and context.peak_hour < 24
    assert "AM" in context.peak_hour_12h or "PM" in context.peak_hour_12h

    # Night owl/early bird flags
    assert isinstance(context.is_night_owl, bool)
    assert isinstance(context.is_early_bird, bool)


def test_narrative_context_to_prompt_string(sample_stats, sample_awards):
    """Test conversion of context to prompt string."""
    context = compile_narrative_context(sample_stats, sample_awards)
    prompt_string = context.to_prompt_string()

    # Should contain key stats
    assert "Year: 2025" in prompt_string
    assert "Total sessions: 3" in prompt_string
    assert "night_owl" in prompt_string
    assert "marathon_coder" in prompt_string


# ===========================
# Tests - Insights Generation
# ===========================


def test_generate_insights_no_api_key(sample_stats, sample_awards):
    """Test graceful handling when no API key available."""
    context = compile_narrative_context(sample_stats, sample_awards)

    with patch("code_wrapped.narrative.insights._check_api_key", return_value=None):
        insights = generate_insights(context)

    assert insights is None


def test_generate_insights_no_anthropic_package(sample_stats, sample_awards):
    """Test graceful handling when anthropic package not installed."""
    context = compile_narrative_context(sample_stats, sample_awards)

    # Mock the import to raise ImportError
    with patch("code_wrapped.narrative.insights._check_api_key", return_value="test-key"):
        with patch("builtins.__import__", side_effect=lambda name, *args, **kwargs:
                   (_ for _ in ()).throw(ImportError()) if name == "anthropic" else __import__(name, *args, **kwargs)):
            insights = generate_insights(context)

    # Should return None when import fails
    assert insights is None


def test_generate_insights_with_mock_api(sample_stats, sample_awards):
    """Test insights generation with mocked Anthropic API."""
    context = compile_narrative_context(sample_stats, sample_awards)

    # Mock API response
    mock_response = Mock()
    mock_response.content = [
        Mock(
            text="""HEADLINE:
You had 3 epic coding sessions in 2025

YEAR_SUMMARY:
Your year was defined by deep focus and late-night breakthroughs. You spent 325 minutes paired with AI, turning ideas into working code.

VIBE_DESCRIPTION:
You're a night owl who thrives in the quiet hours. Your coding style is methodical and persistent.

SURPRISING_INSIGHT:
Your longest session was over 4 hours - that's some serious dedication to solving hard problems.

EPIC_MOMENT:
You crushed 188 conversation turns across just 3 sessions. When you code, you go deep.

PERSONAL_NOTE:
Here's to another year of late-night breakthroughs and creative solutions. Your AI partners are ready when you are."""
        )
    ]

    # Mock Anthropic client
    mock_client = Mock()
    mock_client.messages.create.return_value = mock_response

    # Mock anthropic module
    mock_anthropic = Mock()
    mock_anthropic.Anthropic.return_value = mock_client

    with patch("code_wrapped.narrative.insights._check_api_key", return_value="test-key"):
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            insights = generate_insights(context)

    assert insights is not None
    assert "3 epic coding sessions" in insights.headline
    assert "late-night breakthroughs" in insights.year_summary
    assert "night owl" in insights.vibe_description
    assert "4 hours" in insights.surprising_insight
    assert "188 conversation turns" in insights.epic_moment
    assert "late-night breakthroughs" in insights.personal_note


def test_generate_insights_api_error(sample_stats, sample_awards):
    """Test graceful handling of API errors."""
    context = compile_narrative_context(sample_stats, sample_awards)

    # Mock client that raises an error
    mock_client = Mock()
    mock_client.messages.create.side_effect = Exception("API Error")

    # Mock anthropic module
    mock_anthropic = Mock()
    mock_anthropic.Anthropic.return_value = mock_client

    with patch("code_wrapped.narrative.insights._check_api_key", return_value="test-key"):
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            insights = generate_insights(context)

    # Should return None on error
    assert insights is None


# ===========================
# Tests - Response Parsing
# ===========================


def test_parse_narrative_response():
    """Test parsing of LLM narrative response."""
    response = """HEADLINE:
You coded 847 sessions this year

YEAR_SUMMARY:
It was an epic year of AI-assisted development.
You built amazing things.

VIBE_DESCRIPTION:
You're a focused, persistent coder.

SURPRISING_INSIGHT:
Your peak hour is 2AM.

EPIC_MOMENT:
Longest session: 4.2 hours!

PERSONAL_NOTE:
Keep coding!"""

    sections = _parse_narrative_response(response)

    assert "HEADLINE" in sections
    assert "You coded 847 sessions this year" == sections["HEADLINE"]

    assert "YEAR_SUMMARY" in sections
    assert "epic year" in sections["YEAR_SUMMARY"]
    assert "You built amazing things." in sections["YEAR_SUMMARY"]

    assert "VIBE_DESCRIPTION" in sections
    assert "focused" in sections["VIBE_DESCRIPTION"]

    assert "SURPRISING_INSIGHT" in sections
    assert "2AM" in sections["SURPRISING_INSIGHT"]

    assert "EPIC_MOMENT" in sections
    assert "4.2 hours" in sections["EPIC_MOMENT"]

    assert "PERSONAL_NOTE" in sections
    assert "Keep coding" in sections["PERSONAL_NOTE"]


def test_parse_narrative_response_empty():
    """Test parsing empty response."""
    sections = _parse_narrative_response("")
    assert sections == {}


def test_parse_narrative_response_malformed():
    """Test parsing malformed response."""
    response = "Some random text without proper sections"
    sections = _parse_narrative_response(response)
    # Should return empty dict for malformed input
    assert sections == {}


# ===========================
# Tests - Integration
# ===========================


def test_full_narrative_pipeline(sample_sessions):
    """Test full pipeline from sessions to narrative."""
    # Aggregate stats
    stats = aggregate_stats(sample_sessions, 2025)

    # Create awards
    from code_wrapped.enrichment.awards import detect_awards

    awards = detect_awards(stats)

    # Compile context
    context = compile_narrative_context(stats, awards)

    # Verify context is valid
    assert context.year == 2025
    assert context.total_sessions > 0
    assert context.total_turns > 0

    # Test prompt string generation
    prompt = context.to_prompt_string()
    assert len(prompt) > 0
    assert "Year: 2025" in prompt


def test_narrative_context_with_empty_stats():
    """Test narrative context creation with minimal stats."""
    empty_stats = WrappedStats(
        year=2025,
        generated_at=datetime.now(timezone.utc),
        total_sessions=0,
        total_turns=0,
        total_tokens=0,
    )

    context = compile_narrative_context(empty_stats, [])

    assert context.year == 2025
    assert context.total_sessions == 0
    assert context.award_count == 0
    assert context.favorite_topic is None
    assert context.dominant_vibe is None
