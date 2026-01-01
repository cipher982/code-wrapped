"""Chart generation using Plotly for Code Wrapped."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from ..stats import WrappedStats
from ..parsers.base import AgentType


def generate_activity_heatmap(stats: WrappedStats) -> go.Figure:
    """Generate a heatmap of coding activity by hour and day of week.

    Args:
        stats: Wrapped statistics

    Returns:
        Plotly figure object
    """
    import calendar
    from datetime import datetime

    # Create day of week x hour matrix
    # Initialize 7x24 grid (Sunday=0 to Saturday=6, hours 0-23)
    activity = [[0 for _ in range(24)] for _ in range(7)]

    # Populate from daily sessions
    for date_str, count in stats.daily_sessions.items():
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            day_of_week = date.weekday()  # Monday=0
            # Convert to Sunday=0 format
            day_of_week = (day_of_week + 1) % 7

            # Get hour distribution for this day if available
            # For now, use the overall hour distribution weighted by this day's sessions
            if stats.hours_distribution:
                total_hour_sessions = sum(stats.hours_distribution.values())
                for hour, hour_count in stats.hours_distribution.items():
                    weight = hour_count / total_hour_sessions if total_hour_sessions > 0 else 0
                    activity[day_of_week][hour] += count * weight
        except ValueError:
            continue

    # Create labels
    days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    hours = [f"{h:02d}:00" for h in range(24)]

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=activity,
        x=hours,
        y=days,
        colorscale='Viridis',
        hovertemplate='%{y} at %{x}<br>Sessions: %{z:.1f}<extra></extra>',
    ))

    fig.update_layout(
        title=f'Your Coding Activity Pattern - {stats.year}',
        xaxis_title='Hour of Day',
        yaxis_title='Day of Week',
        height=400,
        font=dict(size=12),
    )

    return fig


def generate_hourly_distribution(stats: WrappedStats) -> go.Figure:
    """Generate a bar chart of sessions by hour of day.

    Args:
        stats: Wrapped statistics

    Returns:
        Plotly figure object
    """
    hours = list(range(24))
    counts = [stats.hours_distribution.get(h, 0) for h in hours]

    fig = go.Figure(data=[
        go.Bar(
            x=hours,
            y=counts,
            marker_color='rgb(55, 83, 109)',
            hovertemplate='%{x}:00<br>Sessions: %{y}<extra></extra>',
        )
    ])

    fig.update_layout(
        title='Sessions by Hour of Day',
        xaxis_title='Hour',
        yaxis_title='Session Count',
        xaxis=dict(tickmode='linear', tick0=0, dtick=2),
        height=400,
    )

    return fig


def generate_tool_usage_chart(stats: WrappedStats, top_n: int = 10) -> go.Figure:
    """Generate horizontal bar chart of top tool usage.

    Args:
        stats: Wrapped statistics
        top_n: Number of top tools to show

    Returns:
        Plotly figure object
    """
    # Get top tools
    sorted_tools = sorted(stats.all_tools.items(), key=lambda x: x[1], reverse=True)[:top_n]

    if not sorted_tools:
        # Return empty figure
        return go.Figure()

    tools, counts = zip(*sorted_tools)

    # Reverse for horizontal bar (top to bottom)
    tools = tools[::-1]
    counts = counts[::-1]

    fig = go.Figure(data=[
        go.Bar(
            x=counts,
            y=tools,
            orientation='h',
            marker_color='rgb(26, 118, 255)',
            hovertemplate='%{y}<br>Uses: %{x}<extra></extra>',
        )
    ])

    fig.update_layout(
        title='Your Tool Fingerprint',
        xaxis_title='Number of Uses',
        yaxis_title='Tool',
        height=max(400, len(tools) * 40),
        showlegend=False,
    )

    return fig


def generate_agent_comparison_chart(stats: WrappedStats) -> go.Figure:
    """Generate pie chart comparing agent usage.

    Args:
        stats: Wrapped statistics

    Returns:
        Plotly figure object
    """
    # Collect agent data
    labels = []
    values = []
    colors = {
        AgentType.CLAUDE: '#5436DA',  # Claude purple
        AgentType.CODEX: '#10A37F',   # OpenAI green
        AgentType.CURSOR: '#000000',  # Black
        AgentType.GEMINI: '#4285F4',  # Google blue
    }

    for agent in AgentType:
        agent_stats = stats.agent_stats.get(agent)
        if agent_stats and agent_stats.session_count > 0:
            labels.append(agent.value.title())
            values.append(agent_stats.session_count)

    if not labels:
        return go.Figure()

    # Get colors in same order
    color_list = [colors.get(AgentType(label.lower()), '#999999') for label in labels]

    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.3,  # Donut chart
            marker=dict(colors=color_list),
            hovertemplate='%{label}<br>%{value} sessions (%{percent})<extra></extra>',
        )
    ])

    fig.update_layout(
        title='Agent Usage Distribution',
        height=400,
    )

    return fig


def generate_topic_distribution_chart(topics_data: list[dict]) -> go.Figure:
    """Generate bar chart of top topics.

    Args:
        topics_data: List of topic dictionaries with 'name', 'count', 'percentage' keys

    Returns:
        Plotly figure object
    """
    if not topics_data:
        return go.Figure()

    names = [t['name'] for t in topics_data]
    percentages = [t['percentage'] for t in topics_data]

    fig = go.Figure(data=[
        go.Bar(
            x=percentages,
            y=names[::-1],  # Reverse for top-to-bottom
            orientation='h',
            marker_color='rgb(99, 110, 250)',
            hovertemplate='%{y}<br>%{x:.1f}% of sessions<extra></extra>',
        )
    ])

    fig.update_layout(
        title='Your Top Coding Topics',
        xaxis_title='Percentage of Sessions',
        yaxis_title='Topic',
        height=max(350, len(names) * 50),
        showlegend=False,
    )

    return fig


def generate_repo_distribution_chart(stats: WrappedStats, top_n: int = 8) -> go.Figure:
    """Generate horizontal bar chart of top repositories.

    Args:
        stats: Wrapped statistics
        top_n: Number of top repos to show

    Returns:
        Plotly figure object
    """
    sorted_repos = sorted(stats.all_repos.items(), key=lambda x: x[1], reverse=True)[:top_n]

    if not sorted_repos:
        return go.Figure()

    repos, counts = zip(*sorted_repos)

    # Reverse for horizontal bar
    repos = repos[::-1]
    counts = counts[::-1]

    fig = go.Figure(data=[
        go.Bar(
            x=counts,
            y=repos,
            orientation='h',
            marker_color='rgb(239, 85, 59)',
            hovertemplate='%{y}<br>Sessions: %{x}<extra></extra>',
        )
    ])

    fig.update_layout(
        title='Your Most Active Repositories',
        xaxis_title='Session Count',
        yaxis_title='Repository',
        height=max(350, len(repos) * 50),
        showlegend=False,
    )

    return fig


def save_chart_as_png(fig: go.Figure, output_path: Path, width: int = 1200, height: int = 800) -> None:
    """Save a Plotly figure as PNG using kaleido.

    Args:
        fig: Plotly figure
        output_path: Path to save PNG file
        width: Image width in pixels
        height: Image height in pixels (None to use figure's height)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use figure's height if it has one
    layout_height = fig.layout.height
    if layout_height and height == 800:  # Only override if default
        height = int(layout_height)

    fig.write_image(str(output_path), width=width, height=height, scale=2)


def generate_all_charts(stats: WrappedStats, enrichment: dict[str, Any]) -> dict[str, go.Figure]:
    """Generate all charts for the wrapped report.

    Args:
        stats: Wrapped statistics
        enrichment: Enrichment data dictionary

    Returns:
        Dictionary mapping chart names to Plotly figures
    """
    charts = {}

    # Core distribution charts
    charts['hourly'] = generate_hourly_distribution(stats)
    charts['heatmap'] = generate_activity_heatmap(stats)

    # Agent and tool usage
    charts['agents'] = generate_agent_comparison_chart(stats)
    charts['tools'] = generate_tool_usage_chart(stats)

    # Repository activity
    if stats.all_repos:
        charts['repos'] = generate_repo_distribution_chart(stats)

    # Topic distribution (if available)
    if enrichment.get('topics'):
        charts['topics'] = generate_topic_distribution_chart(enrichment['topics'])

    return charts
