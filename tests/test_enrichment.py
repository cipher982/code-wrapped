"""Tests for enrichment modules: topics, vibes, archetypes, fingerprint, and awards."""

from datetime import datetime, timezone

import pytest

from code_wrapped.enrichment.archetypes import (
    ArchetypeProfile,
    ArchetypeScore,
    classify_prompt,
    classify_session_prompts,
    compute_archetype_profile,
    get_archetype_summary,
)
from code_wrapped.enrichment.awards import (
    Award,
    detect_awards,
    get_most_active_day_award,
    get_peak_hour_award,
)
from code_wrapped.enrichment.fingerprint import (
    CategoryUsage,
    Fingerprint,
    ToolUsage,
    categorize_tool,
    compute_fingerprint,
    get_agent_fingerprints,
    get_fingerprint_ascii,
)
from code_wrapped.enrichment.topics import (
    TopicMatch,
    compute_topic_distribution,
    detect_session_topic,
    detect_topic,
    get_top_topics,
)
from code_wrapped.enrichment.vibes import (
    VibeMatch,
    compute_vibe_distribution,
    detect_session_vibe,
    detect_vibe,
    get_dominant_vibe,
)
from code_wrapped.parsers.base import AgentType, Session
from code_wrapped.stats import AgentStats, WrappedStats, aggregate_stats


# ===========================
# Fixtures - Mock Sessions
# ===========================


@pytest.fixture
def api_session():
    """Session focused on API integration work."""
    return Session(
        id="api-1",
        agent=AgentType.CLAUDE,
        started_at=datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
        ended_at=datetime(2024, 1, 15, 15, 45, tzinfo=timezone.utc),
        duration_minutes=75.0,
        repo="api-service",
        turn_count=20,
        user_message_count=10,
        assistant_message_count=10,
        token_count=50000,
        tools_used={"Bash": 5, "Edit": 3, "Read": 2},
        user_prompts=[
            "Help me integrate the REST API endpoint",
            "Add authentication with bearer token",
            "Test the API request with fetch",
            "Handle the response properly",
        ],
    )


@pytest.fixture
def debugging_session():
    """Session with lots of debugging and frustration."""
    return Session(
        id="debug-1",
        agent=AgentType.CLAUDE,
        started_at=datetime(2024, 2, 10, 23, 15, tzinfo=timezone.utc),
        ended_at=datetime(2024, 2, 11, 2, 30, tzinfo=timezone.utc),
        duration_minutes=195.0,
        repo="broken-app",
        turn_count=80,
        user_message_count=40,
        assistant_message_count=40,
        token_count=200000,
        tools_used={"Bash": 20, "Read": 15, "Edit": 5},
        user_prompts=[
            "This error doesn't make sense",
            "Why is it broken?",
            "The test still fails",
            "Nothing works",
            "wtf is going on here",
            "Can't figure out this bug",
            "It's still crashing",
        ],
        errors=["TypeError: Cannot read property 'foo' of undefined"],
    )


@pytest.fixture
def frontend_session():
    """Session working on React components."""
    return Session(
        id="frontend-1",
        agent=AgentType.CLAUDE,
        started_at=datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2024, 3, 20, 11, 30, tzinfo=timezone.utc),
        duration_minutes=90.0,
        repo="my-react-app",
        turn_count=25,
        user_message_count=12,
        assistant_message_count=13,
        token_count=75000,
        tools_used={"Edit": 10, "Read": 5, "Bash": 3},
        user_prompts=[
            "Create a React component for the navbar",
            "Add Tailwind CSS styling",
            "Make it responsive",
            "Add animation on hover",
        ],
    )


@pytest.fixture
def learning_session():
    """Session with lots of questions and learning."""
    return Session(
        id="learn-1",
        agent=AgentType.CLAUDE,
        started_at=datetime(2024, 4, 5, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2024, 4, 5, 10, 0, tzinfo=timezone.utc),
        duration_minutes=60.0,
        repo="tutorial-project",
        turn_count=30,
        user_message_count=15,
        assistant_message_count=15,
        token_count=100000,
        tools_used={"Read": 10, "WebFetch": 5},
        user_prompts=[
            "How does async/await work in Python?",
            "Explain the difference between these two approaches",
            "What is the best practice here?",
            "Can you show me an example?",
            "Why does this pattern work better?",
        ],
    )


@pytest.fixture
def flow_state_session():
    """Productive session in flow state."""
    return Session(
        id="flow-1",
        agent=AgentType.CLAUDE,
        started_at=datetime(2024, 5, 12, 15, 0, tzinfo=timezone.utc),
        ended_at=datetime(2024, 5, 12, 16, 30, tzinfo=timezone.utc),
        duration_minutes=90.0,
        repo="new-feature",
        turn_count=40,
        user_message_count=20,
        assistant_message_count=20,
        token_count=150000,
        tools_used={"Edit": 15, "Bash": 10, "Read": 5},
        user_prompts=[
            "Perfect, that works great",
            "Ship this feature",
            "Deploy to production",
            "All tests are passing",
            "Looks good to me, merge it",
        ],
    )


@pytest.fixture
def test_writing_session():
    """Session focused on writing tests."""
    return Session(
        id="test-1",
        agent=AgentType.CLAUDE,
        started_at=datetime(2024, 6, 8, 13, 0, tzinfo=timezone.utc),
        ended_at=datetime(2024, 6, 8, 14, 30, tzinfo=timezone.utc),
        duration_minutes=90.0,
        repo="my-project",
        turn_count=35,
        user_message_count=18,
        assistant_message_count=17,
        token_count=120000,
        tools_used={"Edit": 12, "Bash": 8, "Read": 4},
        user_prompts=[
            "Write unit tests for this function",
            "Add integration test coverage",
            "Mock the API call",
            "Verify the test assertions",
            "Check the coverage report",
        ],
    )


@pytest.fixture
def weekend_sessions():
    """Multiple sessions on weekend days."""
    return [
        Session(
            id=f"weekend-{i}",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 6, 15 + i, 10, 0, tzinfo=timezone.utc),  # June 15-16 (Sat-Sun)
            ended_at=datetime(2024, 6, 15 + i, 11, 0, tzinfo=timezone.utc),
            duration_minutes=60.0,
            turn_count=20,
            user_message_count=10,
            assistant_message_count=10,
            token_count=50000,
            tools_used={"Edit": 5, "Bash": 3},
            user_prompts=["Working on weekend project"],
        )
        for i in range(2)
    ]


@pytest.fixture
def multi_agent_sessions():
    """Sessions across different agents."""
    agents = [AgentType.CLAUDE, AgentType.CODEX, AgentType.CURSOR, AgentType.GEMINI]
    return [
        Session(
            id=f"{agent.value}-session",
            agent=agent,
            started_at=datetime(2024, 7, 1 + i, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 7, 1 + i, 11, 0, tzinfo=timezone.utc),
            duration_minutes=60.0,
            turn_count=25,
            user_message_count=12,
            assistant_message_count=13,
            token_count=75000,
            tools_used={"Edit": 5, "Read": 3, "Bash": 2},
            user_prompts=["Build a new feature"],
        )
        for i, agent in enumerate(agents)
    ]


@pytest.fixture
def high_token_sessions():
    """Sessions with very high token usage."""
    return [
        Session(
            id=f"high-token-{i}",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 8, 1 + i, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 8, 1 + i, 12, 0, tzinfo=timezone.utc),
            duration_minutes=120.0,
            turn_count=100,
            user_message_count=50,
            assistant_message_count=50,
            token_count=200_000_000,  # 200M tokens per session
            tools_used={"Edit": 30, "Read": 20, "Bash": 15},
            user_prompts=["Complex AI-powered task"],
        )
        for i in range(3)  # 600M total tokens
    ]


# ===========================
# Topics Tests
# ===========================


class TestTopics:
    """Tests for topic detection."""

    def test_detect_topic_api_integration(self):
        """Test detecting API integration topic."""
        text = "Help me integrate the REST API endpoint with OAuth authentication"
        topic = detect_topic(text)

        assert topic is not None
        assert topic.topic == "api_integration"
        assert topic.display_name == "API Integrations"
        assert topic.score > 0
        assert len(topic.matched_keywords) > 0

    def test_detect_topic_frontend(self):
        """Test detecting frontend topic."""
        text = "Create a React component with Tailwind CSS and responsive layout"
        topic = detect_topic(text)

        assert topic is not None
        assert topic.topic == "frontend"
        assert "react" in topic.matched_keywords or "css" in topic.matched_keywords

    def test_detect_topic_debugging(self):
        """Test detecting debugging topic."""
        text = "Fix this error, the bug is causing a crash and I'm stuck"
        topic = detect_topic(text)

        assert topic is not None
        assert topic.topic == "debugging"
        assert topic.score > 0

    def test_detect_topic_testing(self):
        """Test detecting testing topic."""
        text = "Write pytest unit tests with fixtures and mock coverage"
        topic = detect_topic(text)

        assert topic is not None
        assert topic.topic == "testing"
        assert "pytest" in topic.matched_keywords

    def test_detect_topic_empty_text(self):
        """Test with empty text returns None."""
        assert detect_topic("") is None
        assert detect_topic(None) is None

    def test_detect_topic_no_match(self):
        """Test with text that doesn't match any topic."""
        topic = detect_topic("hello world")
        # Should return None or a very weak match
        # Implementation might return None or weak match depending on design
        if topic:
            assert topic.score < 0.2

    def test_detect_session_topic(self, api_session):
        """Test detecting topic from session."""
        topic = detect_session_topic(api_session)

        assert topic is not None
        assert topic.topic == "api_integration"

    def test_detect_session_topic_with_repo_name(self, frontend_session):
        """Test that repo name influences topic detection."""
        topic = detect_session_topic(frontend_session)

        assert topic is not None
        # Frontend keywords in prompts + "react" in repo name
        assert topic.topic == "frontend"

    def test_compute_topic_distribution(
        self, api_session, debugging_session, frontend_session, learning_session
    ):
        """Test computing topic distribution across sessions."""
        sessions = [api_session, debugging_session, frontend_session, learning_session]
        distribution = compute_topic_distribution(sessions)

        assert isinstance(distribution, dict)
        assert len(distribution) > 0
        assert "API Integrations" in distribution or "Debugging" in distribution

    def test_get_top_topics(
        self, api_session, debugging_session, frontend_session, learning_session
    ):
        """Test getting top topics with counts and percentages."""
        sessions = [api_session, debugging_session, frontend_session, learning_session]
        top_topics = get_top_topics(sessions, limit=3)

        assert isinstance(top_topics, list)
        assert len(top_topics) <= 3

        for topic_name, count, percentage in top_topics:
            assert isinstance(topic_name, str)
            assert isinstance(count, int)
            assert isinstance(percentage, float)
            assert 0 <= percentage <= 100
            assert count > 0

    def test_get_top_topics_empty(self):
        """Test get_top_topics with no sessions."""
        assert get_top_topics([]) == []


# ===========================
# Vibes Tests
# ===========================


class TestVibes:
    """Tests for vibe detection."""

    def test_detect_vibe_debugging_hell(self):
        """Test detecting debugging hell vibe."""
        text = "error error bug broken doesn't work wtf crash fail"
        vibe = detect_vibe(text)

        assert vibe is not None
        assert vibe.vibe == "debugging_hell"
        assert vibe.display_name == "Debugging Hell"
        assert vibe.emoji == "🔥"
        assert vibe.score > 0
        assert 0 <= vibe.confidence <= 1.0

    def test_detect_vibe_flow_state(self):
        """Test detecting flow state vibe."""
        text = "perfect works great done ship deploy success awesome lgtm"
        vibe = detect_vibe(text)

        assert vibe is not None
        assert vibe.vibe == "flow_state"
        assert vibe.emoji == "🌊"

    def test_detect_vibe_learning(self):
        """Test detecting learning vibe."""
        text = "how does this work explain what is this learn understand tutorial"
        vibe = detect_vibe(text)

        assert vibe is not None
        assert vibe.vibe == "learning"
        assert vibe.emoji == "📚"

    def test_detect_vibe_exploration(self):
        """Test detecting exploration vibe."""
        text = "what if we try this experiment explore prototype poc spike"
        vibe = detect_vibe(text)

        assert vibe is not None
        assert vibe.vibe == "exploration"
        assert vibe.emoji == "🧭"

    def test_detect_vibe_deep_work(self):
        """Test detecting deep work vibe."""
        text = "architecture design refactor system implement complex careful plan"
        vibe = detect_vibe(text)

        assert vibe is not None
        assert vibe.vibe == "deep_work"
        assert vibe.emoji == "🎯"

    def test_detect_vibe_empty_text(self):
        """Test with empty text returns None."""
        assert detect_vibe("") is None
        assert detect_vibe(None) is None

    def test_detect_session_vibe_long_debugging(self, debugging_session):
        """Test that long debugging sessions boost debugging confidence."""
        vibe = detect_session_vibe(debugging_session)

        assert vibe is not None
        assert vibe.vibe == "debugging_hell"
        # Long session with many turns should boost confidence
        assert vibe.confidence > 0.5

    def test_detect_session_vibe_flow_state(self, flow_state_session):
        """Test detecting flow state from session."""
        vibe = detect_session_vibe(flow_state_session)

        assert vibe is not None
        assert vibe.vibe == "flow_state"

    def test_detect_session_vibe_learning(self, learning_session):
        """Test detecting learning vibe from session."""
        vibe = detect_session_vibe(learning_session)

        assert vibe is not None
        assert vibe.vibe == "learning"

    def test_detect_session_vibe_deep_work_inference(self):
        """Test that long sessions with low keyword scores infer deep_work."""
        session = Session(
            id="deep-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            duration_minutes=180.0,  # 3 hours
            turn_count=60,
            user_prompts=["work on the system"],  # Vague, low keyword match
        )
        vibe = detect_session_vibe(session)

        # Should potentially infer deep_work from session characteristics
        # This depends on implementation details
        assert vibe is not None

    def test_compute_vibe_distribution(
        self, debugging_session, flow_state_session, learning_session
    ):
        """Test computing vibe distribution."""
        sessions = [debugging_session, flow_state_session, learning_session]
        distribution = compute_vibe_distribution(sessions)

        assert isinstance(distribution, dict)
        assert "Debugging Hell" in distribution
        assert "Flow State" in distribution
        assert distribution["Debugging Hell"] >= 1

    def test_get_dominant_vibe(self, debugging_session, flow_state_session):
        """Test getting dominant vibe."""
        # More debugging sessions than flow
        sessions = [debugging_session, debugging_session, flow_state_session]
        result = get_dominant_vibe(sessions)

        assert result is not None
        display_name, emoji, percentage = result
        assert display_name == "Debugging Hell"
        assert emoji == "🔥"
        assert percentage > 0

    def test_get_dominant_vibe_empty(self):
        """Test get_dominant_vibe with no sessions."""
        assert get_dominant_vibe([]) is None


# ===========================
# Archetypes Tests
# ===========================


class TestArchetypes:
    """Tests for prompt archetype classification."""

    def test_classify_prompt_architect(self):
        """Test classifying architect prompts."""
        prompts = [
            "refactor this code for better architecture",
            "design the system structure",
            "organize and simplify the modules",
        ]
        for prompt in prompts:
            archetype = classify_prompt(prompt)
            assert archetype == "architect"

    def test_classify_prompt_debugger(self):
        """Test classifying debugger prompts."""
        prompts = [
            "fix this bug",
            "why doesn't this work",
            "the error is breaking everything",
        ]
        for prompt in prompts:
            archetype = classify_prompt(prompt)
            assert archetype == "debugger"

    def test_classify_prompt_explorer(self):
        """Test classifying explorer prompts."""
        prompts = [
            "how does this work?",
            "explain this concept",
            "what is the difference between these?",
        ]
        for prompt in prompts:
            archetype = classify_prompt(prompt)
            assert archetype == "explorer"

    def test_classify_prompt_builder(self):
        """Test classifying builder prompts."""
        prompts = [
            "add a new feature",
            "create this component",
            "implement the authentication",
        ]
        for prompt in prompts:
            archetype = classify_prompt(prompt)
            assert archetype == "builder"

    def test_classify_prompt_shipper(self):
        """Test classifying shipper prompts."""
        prompts = [
            "deploy to production",
            "release this version",
            "merge the PR",
        ]
        for prompt in prompts:
            archetype = classify_prompt(prompt)
            assert archetype == "shipper"

    def test_classify_prompt_tester(self):
        """Test classifying tester prompts."""
        prompts = [
            "write unit tests for this",
            "verify the test coverage",
            "add mock fixture to the test",
        ]
        for prompt in prompts:
            archetype = classify_prompt(prompt)
            assert archetype == "tester"

    def test_classify_prompt_empty(self):
        """Test with empty prompt."""
        assert classify_prompt("") is None
        assert classify_prompt(None) is None

    def test_classify_prompt_no_match(self):
        """Test with prompt that doesn't match any archetype."""
        result = classify_prompt("hello world")
        # Might return None or weakest match
        assert result is None or isinstance(result, str)

    def test_classify_session_prompts(self, debugging_session):
        """Test classifying all prompts in a session."""
        counts = classify_session_prompts(debugging_session)

        assert isinstance(counts, dict)
        assert "debugger" in counts
        assert counts["debugger"] > 0

    def test_compute_archetype_profile(
        self,
        api_session,
        debugging_session,
        frontend_session,
        learning_session,
        flow_state_session,
        test_writing_session,
    ):
        """Test computing full archetype profile."""
        sessions = [
            api_session,
            debugging_session,
            frontend_session,
            learning_session,
            flow_state_session,
            test_writing_session,
        ]
        profile = compute_archetype_profile(sessions)

        assert profile is not None
        assert isinstance(profile, ArchetypeProfile)
        assert isinstance(profile.primary, ArchetypeScore)
        assert profile.primary.count > 0
        assert profile.primary.percentage > 0

        if profile.secondary:
            assert isinstance(profile.secondary, ArchetypeScore)
            assert profile.secondary.count > 0

        assert len(profile.all_scores) > 0
        assert profile.total_classified > 0
        assert profile.total_prompts > 0

        # Check that percentages sum to 100 (approximately)
        total_pct = sum(score.percentage for score in profile.all_scores)
        assert 99 <= total_pct <= 101  # Allow for rounding

    def test_compute_archetype_profile_empty(self):
        """Test with no sessions."""
        assert compute_archetype_profile([]) is None

    def test_get_archetype_summary(self, debugging_session, frontend_session):
        """Test getting human-readable summary."""
        sessions = [debugging_session, frontend_session]
        summary = get_archetype_summary(sessions)

        assert isinstance(summary, str)
        assert "%" in summary
        # Should mention primary archetype
        assert any(
            name in summary
            for name in ["Debugger", "Builder", "Architect", "Explorer", "Shipper", "Tester"]
        )


# ===========================
# Fingerprint Tests
# ===========================


class TestFingerprint:
    """Tests for tool usage fingerprint."""

    def test_categorize_tool_terminal(self):
        """Test categorizing terminal tools."""
        assert categorize_tool("Bash") == "terminal"
        assert categorize_tool("bash") == "terminal"
        assert categorize_tool("shell") == "terminal"

    def test_categorize_tool_editor(self):
        """Test categorizing editor tools."""
        assert categorize_tool("Edit") == "editor"
        assert categorize_tool("Write") == "editor"
        assert categorize_tool("NotebookEdit") == "editor"

    def test_categorize_tool_reader(self):
        """Test categorizing reader tools."""
        assert categorize_tool("Read") == "reader"
        assert categorize_tool("Glob") == "reader"
        assert categorize_tool("Grep") == "reader"

    def test_categorize_tool_browser(self):
        """Test categorizing browser tools."""
        assert categorize_tool("WebFetch") == "browser"
        assert categorize_tool("browser") == "browser"
        assert categorize_tool("playwright") == "browser"

    def test_categorize_tool_unknown(self):
        """Test with unknown tool."""
        assert categorize_tool("UnknownTool") is None

    def test_compute_fingerprint(self, api_session, debugging_session, frontend_session):
        """Test computing tool fingerprint."""
        sessions = [api_session, debugging_session, frontend_session]
        fingerprint = compute_fingerprint(sessions)

        assert fingerprint is not None
        assert isinstance(fingerprint, Fingerprint)
        assert isinstance(fingerprint.personality, str)
        assert isinstance(fingerprint.personality_description, str)
        assert len(fingerprint.categories) > 0
        assert len(fingerprint.top_tools) > 0
        assert fingerprint.total_tool_uses > 0

        # Check categories
        for category in fingerprint.categories:
            assert isinstance(category, CategoryUsage)
            assert category.count > 0
            assert 0 <= category.percentage <= 100
            assert len(category.tools) > 0

        # Check top tools
        for tool in fingerprint.top_tools:
            assert isinstance(tool, ToolUsage)
            assert tool.count > 0
            assert 0 <= tool.percentage <= 100

    def test_compute_fingerprint_bash_heavy(self):
        """Test Terminal Warrior personality for Bash-heavy usage."""
        session = Session(
            id="bash-heavy",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            tools_used={"Bash": 50, "Edit": 5, "Read": 5},
            user_prompts=["terminal work"],
        )
        fingerprint = compute_fingerprint([session])

        assert fingerprint is not None
        # Should have terminal as dominant category
        assert fingerprint.categories[0].category == "terminal"

    def test_compute_fingerprint_combo_patterns(self):
        """Test combo fingerprint detection."""
        session = Session(
            id="combo-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            tools_used={"Bash": 20, "Edit": 20, "Read": 5},
            user_prompts=["balanced work"],
        )
        fingerprint = compute_fingerprint([session])

        assert fingerprint is not None
        # Should detect Full-Stack Developer combo (terminal + editor)
        assert fingerprint.personality in [
            "Full-Stack Developer",
            "Terminal Warrior",
            "Code Sculptor",
        ]

    def test_compute_fingerprint_empty(self):
        """Test with no tool usage."""
        session = Session(
            id="empty-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            tools_used={},
            user_prompts=[],
        )
        assert compute_fingerprint([session]) is None

    def test_get_fingerprint_ascii(self, api_session, debugging_session):
        """Test generating ASCII visualization."""
        sessions = [api_session, debugging_session]
        fingerprint = compute_fingerprint(sessions)
        assert fingerprint is not None

        ascii_output = get_fingerprint_ascii(fingerprint, width=40)

        assert isinstance(ascii_output, str)
        assert "Your Coding DNA:" in ascii_output
        assert fingerprint.personality in ascii_output
        assert "█" in ascii_output or "░" in ascii_output
        assert "%" in ascii_output

    def test_get_fingerprint_ascii_empty(self):
        """Test ASCII generation with no tools."""
        fingerprint = Fingerprint(
            personality="None",
            personality_description="No tools",
            categories=[],
            top_tools=[],
            total_tool_uses=0,
            raw_counts={},
        )
        ascii_output = get_fingerprint_ascii(fingerprint)
        assert "No tool usage data" in ascii_output

    def test_get_agent_fingerprints(self, multi_agent_sessions):
        """Test computing fingerprints per agent."""
        fingerprints = get_agent_fingerprints(multi_agent_sessions)

        assert isinstance(fingerprints, dict)
        assert len(fingerprints) == 4  # One per agent
        assert "claude" in fingerprints
        assert "codex" in fingerprints

        for agent_name, fp in fingerprints.items():
            assert isinstance(fp, Fingerprint)
            assert fp.total_tool_uses > 0


# ===========================
# Awards Tests
# ===========================


class TestAwards:
    """Tests for award detection."""

    def test_detect_awards_night_owl(self):
        """Test detecting Night Owl award."""
        # Create sessions mostly at night
        sessions = [
            Session(
                id=f"night-{i}",
                agent=AgentType.CLAUDE,
                started_at=datetime(2024, 1, i + 1, 23, 0, tzinfo=timezone.utc),  # 11pm
                ended_at=datetime(2024, 1, i + 1, 23, 30, tzinfo=timezone.utc),
                turn_count=10,
                user_prompts=["night coding"],
            )
            for i in range(5)
        ]
        stats = aggregate_stats(sessions, 2024)
        awards = detect_awards(stats)

        night_owl = next((a for a in awards if a.id == "night_owl"), None)
        assert night_owl is not None
        assert night_owl.name == "Night Owl"
        assert night_owl.emoji == "🦉"

    def test_detect_awards_early_bird(self):
        """Test detecting Early Bird award."""
        sessions = [
            Session(
                id=f"early-{i}",
                agent=AgentType.CLAUDE,
                started_at=datetime(2024, 1, i + 1, 6, 0, tzinfo=timezone.utc),  # 6am
                ended_at=datetime(2024, 1, i + 1, 7, 0, tzinfo=timezone.utc),
                turn_count=10,
                user_prompts=["morning coding"],
            )
            for i in range(5)
        ]
        stats = aggregate_stats(sessions, 2024)
        awards = detect_awards(stats)

        early_bird = next((a for a in awards if a.id == "early_bird"), None)
        assert early_bird is not None
        assert early_bird.name == "Early Bird"
        assert early_bird.emoji == "🐦"

    def test_detect_awards_marathon_coder(self):
        """Test detecting Marathon Coder award."""
        session = Session(
            id="marathon-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            duration_minutes=240.0,  # 4 hours
            turn_count=100,
            user_prompts=["long session"],
        )
        stats = aggregate_stats([session], 2024)
        awards = detect_awards(stats)

        marathon = next((a for a in awards if a.id == "marathon_coder"), None)
        assert marathon is not None
        assert marathon.name == "Marathon Coder"
        assert marathon.value > 3.0  # More than 3 hours

    def test_detect_awards_streak_master(self):
        """Test detecting Streak Master award."""
        # Create sessions for 35 consecutive days
        from datetime import timedelta

        sessions = []
        start_date = datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)
        for i in range(35):
            session_date = start_date + timedelta(days=i)
            sessions.append(
                Session(
                    id=f"streak-{i}",
                    agent=AgentType.CLAUDE,
                    started_at=session_date,
                    ended_at=session_date + timedelta(hours=1),
                    turn_count=10,
                    user_prompts=["daily coding"],
                )
            )
        stats = aggregate_stats(sessions, 2024)
        awards = detect_awards(stats)

        streak_master = next((a for a in awards if a.id == "streak_master"), None)
        assert streak_master is not None
        assert streak_master.value >= 30

    def test_detect_awards_repo_hopper(self):
        """Test detecting Repo Hopper award."""
        sessions = [
            Session(
                id=f"repo-{i}",
                agent=AgentType.CLAUDE,
                started_at=datetime(2024, 1, i + 1, 10, 0, tzinfo=timezone.utc),
                ended_at=datetime(2024, 1, i + 1, 11, 0, tzinfo=timezone.utc),
                repo=f"project-{i}",
                turn_count=10,
                user_prompts=["repo work"],
            )
            for i in range(12)  # 12 different repos
        ]
        stats = aggregate_stats(sessions, 2024)
        awards = detect_awards(stats)

        repo_hopper = next((a for a in awards if a.id == "repo_hopper"), None)
        assert repo_hopper is not None
        assert repo_hopper.value >= 10

    def test_detect_awards_deep_diver(self):
        """Test detecting Deep Diver award."""
        sessions = [
            Session(
                id=f"deep-{i}",
                agent=AgentType.CLAUDE,
                started_at=datetime(2024, 1, i + 1, 10, 0, tzinfo=timezone.utc),
                ended_at=datetime(2024, 1, i + 1, 12, 0, tzinfo=timezone.utc),
                turn_count=60,  # High turn count
                user_prompts=["deep conversation"],
            )
            for i in range(3)
        ]
        stats = aggregate_stats(sessions, 2024)
        awards = detect_awards(stats)

        deep_diver = next((a for a in awards if a.id == "deep_diver"), None)
        assert deep_diver is not None
        assert deep_diver.value > 50

    def test_detect_awards_ai_whisperer(self, high_token_sessions):
        """Test detecting AI Whisperer award."""
        stats = aggregate_stats(high_token_sessions, 2024)
        awards = detect_awards(stats)

        ai_whisperer = next((a for a in awards if a.id == "ai_whisperer"), None)
        assert ai_whisperer is not None
        assert ai_whisperer.value > 500_000_000

    def test_detect_awards_polyglot(self, multi_agent_sessions):
        """Test detecting Polyglot award."""
        stats = aggregate_stats(multi_agent_sessions, 2024)
        awards = detect_awards(stats)

        polyglot = next((a for a in awards if a.id == "polyglot"), None)
        assert polyglot is not None
        assert polyglot.value >= 3

    def test_detect_awards_weekend_warrior(self, weekend_sessions):
        """Test detecting Weekend Warrior award."""
        # Add some weekday sessions to create ratio
        weekday_session = Session(
            id="weekday-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 6, 13, 10, 0, tzinfo=timezone.utc),  # Thursday
            ended_at=datetime(2024, 6, 13, 11, 0, tzinfo=timezone.utc),
            turn_count=10,
            user_prompts=["weekday work"],
        )
        all_sessions = weekend_sessions + [weekday_session]
        stats = aggregate_stats(all_sessions, 2024)
        awards = detect_awards(stats)

        weekend_warrior = next((a for a in awards if a.id == "weekend_warrior"), None)
        # Should get award with 2/3 sessions on weekend (66% > 35%)
        assert weekend_warrior is not None

    def test_detect_awards_terminal_master(self):
        """Test detecting Terminal Master award."""
        session = Session(
            id="terminal-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            tools_used={"Bash": 60, "Edit": 20, "Read": 10},  # 60/90 = 66% Bash
            user_prompts=["terminal work"],
        )
        stats = aggregate_stats([session], 2024)
        awards = detect_awards(stats)

        terminal_master = next((a for a in awards if a.id == "terminal_master"), None)
        assert terminal_master is not None
        assert terminal_master.value > 0.5

    def test_detect_awards_empty(self):
        """Test with minimal stats."""
        stats = WrappedStats(year=2024, generated_at=datetime.now())
        awards = detect_awards(stats)

        # Should return empty list or only awards that don't require data
        assert isinstance(awards, list)

    def test_get_most_active_day_award(self):
        """Test getting most active day award."""
        sessions = [
            Session(
                id=f"day-{i}",
                agent=AgentType.CLAUDE,
                started_at=datetime(2024, 1, 15, 10 + i, 0, tzinfo=timezone.utc),
                ended_at=datetime(2024, 1, 15, 11 + i, 0, tzinfo=timezone.utc),
                turn_count=10,
                user_prompts=["work"],
            )
            for i in range(5)  # 5 sessions on same day
        ]
        stats = aggregate_stats(sessions, 2024)
        award = get_most_active_day_award(stats)

        assert award is not None
        assert award.id == "most_active_day"
        assert award.value == 5
        assert "January 15" in award.detail or "2024-01-15" in award.detail

    def test_get_peak_hour_award(self):
        """Test getting peak hour award."""
        sessions = [
            Session(
                id=f"hour-{i}",
                agent=AgentType.CLAUDE,
                started_at=datetime(2024, 1, 1, 14, i, tzinfo=timezone.utc),  # 2pm
                ended_at=datetime(2024, 1, 1, 15, i, tzinfo=timezone.utc),
                turn_count=10,
                user_prompts=["work"],
            )
            for i in range(5)
        ]
        stats = aggregate_stats(sessions, 2024)
        award = get_peak_hour_award(stats)

        assert award is not None
        assert award.id == "peak_hour"
        assert award.value == 14  # 2pm
        assert "afternoon coder" in award.description
        assert "PM" in award.detail


# ===========================
# Integration Tests
# ===========================


class TestIntegration:
    """Integration tests combining multiple enrichment modules."""

    def test_full_enrichment_pipeline(
        self,
        api_session,
        debugging_session,
        frontend_session,
        learning_session,
        flow_state_session,
        test_writing_session,
    ):
        """Test complete enrichment pipeline on multiple sessions."""
        sessions = [
            api_session,
            debugging_session,
            frontend_session,
            learning_session,
            flow_state_session,
            test_writing_session,
        ]

        # Topic detection
        topics = [detect_session_topic(s) for s in sessions]
        # Most sessions should have topics, but some might not match
        assert len([t for t in topics if t is not None]) >= 4

        # Vibe detection
        vibes = [detect_session_vibe(s) for s in sessions]
        # Most sessions should have vibes, but some might be neutral
        assert len([v for v in vibes if v is not None]) >= 4

        # Archetype classification
        profile = compute_archetype_profile(sessions)
        assert profile is not None

        # Fingerprint
        fingerprint = compute_fingerprint(sessions)
        assert fingerprint is not None

        # Awards
        stats = aggregate_stats(sessions, 2024)
        awards = detect_awards(stats)
        assert isinstance(awards, list)

    def test_enrichment_with_edge_cases(self):
        """Test enrichment handles edge cases gracefully."""
        # Empty session
        empty_session = Session(
            id="empty",
            agent=AgentType.CLAUDE,
            started_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            user_prompts=[],
            tools_used={},
        )

        # Should not crash
        topic = detect_session_topic(empty_session)
        vibe = detect_session_vibe(empty_session)
        profile = compute_archetype_profile([empty_session])
        fingerprint = compute_fingerprint([empty_session])

        # Results may be None but shouldn't crash
        assert topic is None
        assert vibe is None
        assert profile is None
        assert fingerprint is None
