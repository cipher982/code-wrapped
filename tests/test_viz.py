"""Tests for visualization modules."""

from datetime import datetime
from pathlib import Path

import pytest

from code_wrapped.parsers.base import AgentType
from code_wrapped.stats import AgentStats, WrappedStats
from code_wrapped.viz.charts import (
    generate_activity_heatmap,
    generate_agent_comparison_chart,
    generate_all_charts,
    generate_hourly_distribution,
    generate_tool_usage_chart,
)
from code_wrapped.viz.cards import (
    generate_agent_comparison_card,
    generate_all_cards,
    generate_hero_card,
)


@pytest.fixture
def sample_stats() -> WrappedStats:
    """Create sample stats for testing."""
    stats = WrappedStats(
        year=2025,
        generated_at=datetime.now(),
        total_sessions=100,
        total_turns=1000,
        total_tokens=50000,
        total_duration_minutes=6000,
        active_days=30,
        longest_streak_days=10,
        all_repos={'repo1': 50, 'repo2': 30, 'repo3': 20},
        all_tools={'Bash': 100, 'Read': 80, 'Edit': 60, 'Write': 40},
        hours_distribution={9: 10, 10: 15, 11: 20, 12: 15, 13: 10},
        daily_sessions={'2025-01-01': 5, '2025-01-02': 8, '2025-01-03': 6},
        most_active_day='2025-01-02',
        most_active_day_sessions=8,
        peak_hour=11,
    )

    # Add agent stats
    claude_stats = AgentStats(
        agent=AgentType.CLAUDE,
        session_count=60,
        turn_count=600,
        token_count=30000,
        total_duration_minutes=3600,
        repos={'repo1': 30, 'repo2': 20, 'repo3': 10},
        tools_used={'Bash': 60, 'Read': 50, 'Edit': 40},
    )
    codex_stats = AgentStats(
        agent=AgentType.CODEX,
        session_count=40,
        turn_count=400,
        token_count=20000,
        total_duration_minutes=2400,
        repos={'repo1': 20, 'repo2': 10, 'repo3': 10},
        tools_used={'Bash': 40, 'Read': 30, 'Write': 40},
    )

    stats.agent_stats[AgentType.CLAUDE] = claude_stats
    stats.agent_stats[AgentType.CODEX] = codex_stats

    return stats


@pytest.fixture
def sample_enrichment() -> dict:
    """Create sample enrichment data."""
    return {
        'topics': [
            {'name': 'API Development', 'count': 30, 'percentage': 30.0},
            {'name': 'Bug Fixing', 'count': 25, 'percentage': 25.0},
        ],
        'fingerprint': {
            'personality': 'Command Line Warrior',
            'description': 'You prefer terminal commands over everything',
            'top_tools': [
                {'name': 'Bash', 'count': 100, 'percentage': 40.0},
                {'name': 'Read', 'count': 80, 'percentage': 32.0},
                {'name': 'Edit', 'count': 60, 'percentage': 24.0},
            ],
        },
        'awards': [
            {
                'id': 'night_owl',
                'name': 'Night Owl',
                'emoji': '🦉',
                'description': 'Late night coder',
                'detail': 'Peak productivity at 2 AM',
            }
        ],
    }


class TestCharts:
    """Test chart generation functions."""

    def test_generate_hourly_distribution(self, sample_stats):
        """Test hourly distribution chart generation."""
        fig = generate_hourly_distribution(sample_stats)
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.layout.title.text == 'Sessions by Hour of Day'

    def test_generate_activity_heatmap(self, sample_stats):
        """Test activity heatmap generation."""
        fig = generate_activity_heatmap(sample_stats)
        assert fig is not None
        assert len(fig.data) == 1
        assert 'heatmap' in fig.data[0].type.lower()

    def test_generate_tool_usage_chart(self, sample_stats):
        """Test tool usage chart generation."""
        fig = generate_tool_usage_chart(sample_stats)
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.layout.title.text == 'Your Tool Fingerprint'

    def test_generate_agent_comparison_chart(self, sample_stats):
        """Test agent comparison chart generation."""
        fig = generate_agent_comparison_chart(sample_stats)
        assert fig is not None
        assert len(fig.data) == 1
        # Should be pie chart
        assert hasattr(fig.data[0], 'hole')  # Donut chart

    def test_generate_all_charts(self, sample_stats, sample_enrichment):
        """Test generating all charts at once."""
        charts = generate_all_charts(sample_stats, sample_enrichment)
        assert isinstance(charts, dict)
        assert 'hourly' in charts
        assert 'heatmap' in charts
        assert 'agents' in charts
        assert 'tools' in charts
        assert 'topics' in charts


class TestCards:
    """Test card generation functions."""

    def test_generate_hero_card(self, sample_stats):
        """Test hero card generation."""
        card = generate_hero_card(sample_stats)
        assert card is not None
        assert card.size == (1200, 630)
        assert card.mode == 'RGB'

    def test_generate_agent_comparison_card(self, sample_stats):
        """Test agent comparison card generation."""
        card = generate_agent_comparison_card(sample_stats)
        assert card is not None
        assert card.size == (1200, 630)

    def test_generate_all_cards(self, sample_stats, sample_enrichment, tmp_path):
        """Test generating all cards at once."""
        output_dir = tmp_path / "cards"
        cards = generate_all_cards(sample_stats, sample_enrichment, output_dir)

        assert len(cards) > 0
        assert output_dir.exists()

        # Check that files were created
        for card_path in cards:
            assert card_path.exists()
            assert card_path.suffix == '.png'

        # Should have at least hero and agent comparison
        card_names = [c.name for c in cards]
        assert 'hero-stats.png' in card_names
        assert 'agent-comparison.png' in card_names


class TestOutput:
    """Test output report generation."""

    def test_generate_html_report(self, sample_stats, sample_enrichment, tmp_path):
        """Test HTML report generation."""
        from code_wrapped.output.report import generate_html_report

        output_path = tmp_path / "wrapped-2025.html"
        result = generate_html_report(sample_stats, sample_enrichment, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Check HTML contains expected elements
        html_content = output_path.read_text()
        assert '<!DOCTYPE html>' in html_content
        assert 'Code Wrapped 2025' in html_content
        assert 'Plotly' in html_content  # Chart library
        assert str(sample_stats.total_sessions) in html_content

    def test_generate_full_report(self, sample_stats, sample_enrichment, tmp_path):
        """Test full report generation."""
        from code_wrapped.output.report import generate_full_report

        outputs = generate_full_report(
            sample_stats,
            tmp_path,
            generate_cards=True,
            narrative=None,
        )

        assert 'html' in outputs
        assert 'cards' in outputs
        assert 'share_json' in outputs

        # Check HTML exists
        assert outputs['html'].exists()

        # Check cards exist
        assert len(outputs['cards']) > 0

        # Check share JSON exists
        assert outputs['share_json'].exists()

        # Verify share JSON has expected structure
        import json
        with open(outputs['share_json']) as f:
            share_data = json.load(f)

        assert share_data['year'] == 2025
        assert 'summary' in share_data
        assert 'agents' in share_data
