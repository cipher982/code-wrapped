"""HTML report generation orchestration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..stats import WrappedStats
from ..viz.charts import generate_all_charts
from ..viz.cards import generate_all_cards


def get_template_env() -> Environment:
    """Get Jinja2 environment for templates.

    Returns:
        Jinja2 Environment configured for templates
    """
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    return env


def charts_to_json(charts: dict[str, Any]) -> str:
    """Convert Plotly charts to JSON for embedding in HTML.

    Args:
        charts: Dictionary of chart name to Plotly figure

    Returns:
        JSON string of chart data
    """
    chart_data = {}

    for name, fig in charts.items():
        # Convert Plotly figure to JSON-serializable dict
        chart_data[name] = {
            'data': fig.to_dict()['data'],
            'layout': fig.to_dict()['layout'],
        }

    return json.dumps(chart_data)


def generate_html_report(
    stats: WrappedStats,
    enrichment: dict[str, Any],
    output_path: Path,
    narrative: dict[str, str] | None = None,
) -> Path:
    """Generate the full HTML report.

    Args:
        stats: Wrapped statistics
        enrichment: Enrichment data dictionary
        output_path: Path to save HTML file
        narrative: Optional LLM-generated narrative

    Returns:
        Path to generated HTML file
    """
    # Generate all charts
    charts = generate_all_charts(stats, enrichment)

    # Convert charts to JSON
    charts_json = charts_to_json(charts)

    # Prepare template context
    context = {
        'year': stats.year,
        'generated_at': stats.generated_at.strftime('%B %d, %Y at %I:%M %p'),
        'summary': {
            'total_sessions': stats.total_sessions,
            'total_turns': stats.total_turns,
            'total_tokens': stats.total_tokens,
            'total_duration_hours': stats.total_duration_minutes / 60,
            'active_days': stats.active_days,
            'longest_streak_days': stats.longest_streak_days,
        },
        'agents': {},
        'distributions': {
            'by_hour': dict(sorted(stats.hours_distribution.items())),
            'by_day': dict(sorted(stats.daily_sessions.items())),
            'by_repo': dict(sorted(stats.all_repos.items(), key=lambda x: x[1], reverse=True)[:10]),
            'by_tool': dict(sorted(stats.all_tools.items(), key=lambda x: x[1], reverse=True)[:15]),
        },
        'enrichment': enrichment,
        'narrative': narrative,
        'charts_json': charts_json,
    }

    # Add per-agent data
    for agent, agent_stats in stats.agent_stats.items():
        if agent_stats.session_count > 0:
            context['agents'][agent.value] = {
                'sessions': agent_stats.session_count,
                'turns': agent_stats.turn_count,
                'tokens': agent_stats.token_count,
                'avg_turns_per_session': agent_stats.avg_turns_per_session,
                'avg_duration_minutes': agent_stats.avg_duration_minutes,
                'top_repos': dict(sorted(agent_stats.repos.items(), key=lambda x: x[1], reverse=True)[:5]),
                'top_tools': dict(sorted(agent_stats.tools_used.items(), key=lambda x: x[1], reverse=True)[:10]),
            }

    # Render template
    env = get_template_env()
    template = env.get_template('wrapped.html')
    html = template.render(**context)

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')

    return output_path


def generate_full_report(
    stats: WrappedStats,
    output_dir: Path,
    generate_cards: bool = True,
    narrative: dict[str, str] | None = None,
) -> dict[str, Path]:
    """Generate complete wrapped report with HTML and cards.

    Args:
        stats: Wrapped statistics
        output_dir: Directory to save all outputs
        generate_cards: Whether to generate PNG cards
        narrative: Optional LLM-generated narrative

    Returns:
        Dictionary mapping output types to paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}

    # Get enrichment data
    enrichment = stats._compute_enrichment() if stats.sessions else {}

    # Generate HTML report
    html_path = output_dir / f"wrapped-{stats.year}.html"
    generate_html_report(stats, enrichment, html_path, narrative)
    outputs['html'] = html_path

    # Generate PNG cards
    if generate_cards:
        cards_dir = output_dir / "cards"
        card_paths = generate_all_cards(stats, enrichment, cards_dir)
        outputs['cards'] = card_paths

    # Save shareable JSON (privacy-safe version)
    share_data = {
        'year': stats.year,
        'summary': {
            'total_sessions': stats.total_sessions,
            'total_turns': stats.total_turns,
            'total_duration_hours': round(stats.total_duration_minutes / 60, 1),
            'active_days': stats.active_days,
        },
        'agents': {
            agent.value: {
                'sessions': agent_stats.session_count,
                'percentage': round((agent_stats.session_count / stats.total_sessions * 100), 1)
            }
            for agent, agent_stats in stats.agent_stats.items()
            if agent_stats.session_count > 0
        },
        'enrichment': {
            k: v for k, v in enrichment.items()
            if k in ['vibe', 'archetype', 'fingerprint', 'awards', 'topics']
        }
    }

    share_path = output_dir / f"wrapped-{stats.year}-share.json"
    with open(share_path, 'w') as f:
        json.dump(share_data, f, indent=2)
    outputs['share_json'] = share_path

    return outputs


def load_wrapped_json(json_path: Path) -> tuple[WrappedStats, dict[str, Any]]:
    """Load wrapped stats from JSON file.

    Args:
        json_path: Path to wrapped-{year}.json

    Returns:
        Tuple of (WrappedStats, enrichment_dict)
    """
    with open(json_path) as f:
        data = json.load(f)

    # We need to reconstruct the WrappedStats object from JSON
    # This is a simplified loader - in practice you might want to
    # re-run the full analysis. For now, we'll just use the JSON data directly.

    from ..parsers.base import AgentType

    stats = WrappedStats(
        year=data['year'],
        generated_at=datetime.fromisoformat(data['generated_at']),
        total_sessions=data['summary']['total_sessions'],
        total_turns=data['summary']['total_turns'],
        total_tokens=data['summary'].get('total_tokens', 0),
        total_duration_minutes=data['summary']['total_duration_hours'] * 60,
        active_days=data['summary']['active_days'],
        longest_streak_days=data['summary']['longest_streak_days'],
        current_streak_days=data['summary'].get('current_streak_days', 0),
        all_repos=data['distributions'].get('by_repo', {}),
        all_tools=data['distributions'].get('by_tool', {}),
        hours_distribution={int(k): v for k, v in data['distributions'].get('by_hour', {}).items()},
        daily_sessions=data['distributions'].get('by_day', {}),
    )

    # Populate agent stats
    for agent_name, agent_data in data.get('agents', {}).items():
        try:
            agent_type = AgentType(agent_name)
            from ..stats import AgentStats
            agent_stats = AgentStats(
                agent=agent_type,
                session_count=agent_data['sessions'],
                turn_count=agent_data['turns'],
                token_count=agent_data.get('tokens', 0),
                total_duration_minutes=agent_data.get('avg_duration_minutes', 0) * agent_data['sessions'],
                repos=agent_data.get('top_repos', {}),
                tools_used=agent_data.get('top_tools', {}),
            )
            stats.agent_stats[agent_type] = agent_stats
        except ValueError:
            continue

    # Get enrichment
    enrichment = data.get('enrichment', {})

    return stats, enrichment
