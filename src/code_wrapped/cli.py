"""CLI entry point for Code Wrapped."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .parsers import (
    parse_claude_sessions,
    parse_codex_sessions,
    parse_cursor_sessions,
    parse_gemini_sessions,
)
from .parsers.base import AgentType, Session
from .stats import WrappedStats, aggregate_stats
from .enrichment import (
    compute_archetype_profile,
    compute_fingerprint,
    detect_awards,
    get_dominant_vibe,
    get_most_active_day_award,
    get_peak_hour_award,
    get_top_topics,
)
from .narrative import compile_narrative_context, generate_insights

console = Console()


def collect_all_sessions(year: int, verbose: bool = False) -> list[Session]:
    """Collect sessions from all agents for a given year."""
    sessions: list[Session] = []

    parsers = [
        ("Claude", parse_claude_sessions),
        ("Codex", parse_codex_sessions),
        ("Cursor", parse_cursor_sessions),
        ("Gemini", parse_gemini_sessions),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for name, parser in parsers:
            task = progress.add_task(f"Parsing {name} sessions...", total=None)
            agent_sessions = list(parser(year=year))
            sessions.extend(agent_sessions)
            progress.update(task, completed=True)

            if verbose:
                console.print(f"  [dim]{name}: {len(agent_sessions)} sessions[/dim]")

    return sessions


def print_narrative(stats: WrappedStats, awards: list) -> None:
    """Print LLM-generated narrative if available."""
    from .narrative import Insights

    # Compile context
    context = compile_narrative_context(stats, awards)

    console.print()
    console.print("[bold cyan]Generating your personalized narrative...[/bold cyan]")
    console.print()

    # Generate insights
    insights = generate_insights(context)

    if not insights:
        console.print(
            "[yellow]Narrative generation unavailable (ANTHROPIC_API_KEY not set)[/yellow]"
        )
        return

    # Print narrative sections
    console.print(
        Panel.fit(
            f"[bold white]{insights.headline}[/bold white]",
            border_style="magenta",
            title="Your Year in Code",
        )
    )
    console.print()

    console.print("[bold]Your Year Summary:[/bold]")
    console.print(f"[white]{insights.year_summary}[/white]")
    console.print()

    console.print("[bold]Your Coding Vibe:[/bold]")
    console.print(f"[white]{insights.vibe_description}[/white]")
    console.print()

    console.print("[bold]Surprising Insight:[/bold]")
    console.print(f"[cyan]{insights.surprising_insight}[/cyan]")
    console.print()

    console.print("[bold]Epic Moment:[/bold]")
    console.print(f"[green]{insights.epic_moment}[/green]")
    console.print()

    console.print("[bold]Looking Ahead:[/bold]")
    console.print(f"[white]{insights.personal_note}[/white]")
    console.print()


def print_summary(stats: WrappedStats) -> None:
    """Print a summary of the wrapped stats to the console."""
    sessions = stats.sessions

    # Header
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]Code Wrapped {stats.year}[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    # Big numbers
    console.print(f"[bold green]{stats.total_sessions:,}[/bold green] sessions")
    console.print(f"[bold green]{stats.total_turns:,}[/bold green] conversation turns")
    if stats.total_tokens:
        console.print(f"[bold green]{stats.total_tokens:,}[/bold green] tokens consumed")
    console.print(
        f"[bold green]{stats.total_duration_minutes / 60:.1f}[/bold green] hours of AI pair programming"
    )
    console.print()

    # Agent breakdown
    table = Table(title="By Agent", show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan")
    table.add_column("Sessions", justify="right")
    table.add_column("Turns", justify="right")
    table.add_column("Avg Turns", justify="right")
    table.add_column("Hours", justify="right")

    for agent in AgentType:
        agent_stats = stats.agent_stats.get(agent)
        if agent_stats and agent_stats.session_count > 0:
            table.add_row(
                agent.value.title(),
                f"{agent_stats.session_count:,}",
                f"{agent_stats.turn_count:,}",
                f"{agent_stats.avg_turns_per_session:.0f}",
                f"{agent_stats.total_duration_minutes / 60:.1f}",
            )

    console.print(table)
    console.print()

    # === ENRICHMENT: Topics ===
    if sessions:
        top_topics = get_top_topics(sessions, limit=5)
        if top_topics:
            console.print("[bold]Your Top Topics:[/bold]")
            for topic, count, pct in top_topics:
                bar_len = int(pct / 5)  # Scale to ~20 chars max
                bar = "█" * bar_len
                console.print(f"  {topic}: [cyan]{bar}[/cyan] {pct:.1f}%")
            console.print()

    # === ENRICHMENT: Vibe ===
    if sessions:
        dominant_vibe = get_dominant_vibe(sessions)
        if dominant_vibe:
            name, emoji, pct = dominant_vibe
            console.print(f"[bold]Your Vibe:[/bold] {emoji} {name} ({pct:.0f}% of sessions)")
            console.print()

    # === ENRICHMENT: Archetype ===
    if sessions:
        profile = compute_archetype_profile(sessions)
        if profile:
            console.print("[bold]Your Coding Archetype:[/bold]")
            console.print(
                f"  {profile.primary.emoji} [bold]{profile.primary.display_name}[/bold] "
                f"({profile.primary.percentage:.0f}%)"
            )
            console.print(f"  [dim]{profile.primary.description}[/dim]")
            if profile.secondary:
                console.print(
                    f"  Secondary: {profile.secondary.emoji} {profile.secondary.display_name} "
                    f"({profile.secondary.percentage:.0f}%)"
                )
            console.print()

    # === ENRICHMENT: Tool Fingerprint ===
    if sessions:
        fingerprint = compute_fingerprint(sessions)
        if fingerprint:
            console.print("[bold]Your Coding DNA:[/bold]")
            console.print(f"  [bold cyan]{fingerprint.personality}[/bold cyan]")
            console.print(f"  [dim]{fingerprint.personality_description}[/dim]")
            console.print()
            # Show top 5 tools as mini bars
            for tool in fingerprint.top_tools[:5]:
                bar_len = int(tool.percentage / 3)  # Scale
                bar = "█" * bar_len + "░" * (20 - bar_len)
                console.print(f"  {tool.name[:12]:12} [cyan]{bar}[/cyan] {tool.percentage:.1f}%")
            console.print()

    # Top repos
    if stats.all_repos:
        console.print("[bold]Top Repositories:[/bold]")
        for repo, count in sorted(stats.all_repos.items(), key=lambda x: x[1], reverse=True)[:5]:
            console.print(f"  {repo}: {count} sessions")
        console.print()

    # === ENRICHMENT: Awards ===
    awards = detect_awards(stats)
    # Add special awards
    active_day_award = get_most_active_day_award(stats)
    if active_day_award:
        awards.append(active_day_award)
    peak_hour_award = get_peak_hour_award(stats)
    if peak_hour_award:
        awards.append(peak_hour_award)

    if awards:
        console.print("[bold]Your Awards:[/bold]")
        for award in awards[:8]:  # Limit to 8 awards
            console.print(f"  {award.emoji} [bold]{award.name}[/bold]")
            console.print(f"     [dim]{award.detail}[/dim]")
        console.print()

    # Fun facts
    console.print("[bold]Fun Facts:[/bold]")
    console.print(f"  Peak productivity hour: {stats.peak_hour}:00")
    console.print(f"  Most active day: {stats.most_active_day} ({stats.most_active_day_sessions} sessions)")
    console.print(f"  Active days: {stats.active_days}")
    console.print(f"  Longest streak: {stats.longest_streak_days} days")
    console.print()


@click.group()
def main():
    """Code Wrapped: Your AI Coding Year in Review."""
    pass


@main.command()
@click.option("--year", "-y", default=datetime.now().year, help="Year to analyze")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file path")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.option(
    "--narrate",
    "-n",
    is_flag=True,
    help="Generate LLM-powered narrative (requires ANTHROPIC_API_KEY)",
)
def run(year: int, output: str | None, verbose: bool, narrate: bool):
    """Generate your Code Wrapped stats."""
    console.print(f"\n[bold]Generating Code Wrapped for {year}...[/bold]\n")

    # Collect sessions
    sessions = collect_all_sessions(year, verbose=verbose)

    if not sessions:
        console.print(f"[yellow]No sessions found for {year}.[/yellow]")
        return

    console.print(f"\n[green]Found {len(sessions)} total sessions![/green]\n")

    # Compute stats
    stats = aggregate_stats(sessions, year)

    # Collect awards for narrative context
    awards = detect_awards(stats)
    active_day_award = get_most_active_day_award(stats)
    if active_day_award:
        awards.append(active_day_award)
    peak_hour_award = get_peak_hour_award(stats)
    if peak_hour_award:
        awards.append(peak_hour_award)

    # Print narrative if requested
    if narrate:
        print_narrative(stats, awards)

    # Print summary
    print_summary(stats)

    # Save output
    if output:
        output_path = Path(output)
    else:
        output_path = Path(f"data/output/wrapped-{year}.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(stats.to_dict(), f, indent=2)

    console.print(f"[dim]Stats saved to: {output_path}[/dim]")


@main.command()
@click.option("--year", "-y", default=datetime.now().year, help="Year to analyze")
def test(year: int):
    """Quick test of parsers without full stats."""
    console.print(f"\n[bold]Testing parsers for {year}...[/bold]\n")

    from .parsers.claude import get_claude_sessions_dir
    from .parsers.codex import get_codex_sessions_dir
    from .parsers.cursor import get_cursor_db_path
    from .parsers.gemini import get_gemini_sessions_dir

    # Check paths
    paths = [
        ("Claude", get_claude_sessions_dir()),
        ("Codex", get_codex_sessions_dir()),
        ("Cursor", get_cursor_db_path()),
        ("Gemini", get_gemini_sessions_dir()),
    ]

    for name, path in paths:
        exists = "[green]EXISTS[/green]" if path.exists() else "[red]NOT FOUND[/red]"
        console.print(f"  {name}: {path} {exists}")

    console.print()

    # Parse a few sessions from each
    sessions = collect_all_sessions(year, verbose=True)
    console.print(f"\n[bold]Total sessions found: {len(sessions)}[/bold]")

    # Show sample
    if sessions:
        console.print("\n[bold]Sample sessions:[/bold]")
        for session in sessions[:5]:
            console.print(
                f"  [{session.agent.value}] {session.date_str} - "
                f"{session.repo or 'unknown'} - {session.turn_count} turns"
            )


if __name__ == "__main__":
    main()
