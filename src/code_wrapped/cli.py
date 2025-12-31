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


def print_summary(stats: WrappedStats) -> None:
    """Print a summary of the wrapped stats to the console."""
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

    # Top repos
    if stats.all_repos:
        console.print("[bold]Top Repositories:[/bold]")
        for repo, count in sorted(stats.all_repos.items(), key=lambda x: x[1], reverse=True)[:5]:
            console.print(f"  {repo}: {count} sessions")
        console.print()

    # Top tools
    if stats.all_tools:
        console.print("[bold]Top Tools:[/bold]")
        for tool, count in sorted(stats.all_tools.items(), key=lambda x: x[1], reverse=True)[:5]:
            console.print(f"  {tool}: {count} uses")
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
def run(year: int, output: str | None, verbose: bool):
    """Generate your Code Wrapped stats."""
    console.print(f"\n[bold]Generating Code Wrapped for {year}...[/bold]\n")

    # Collect sessions
    sessions = collect_all_sessions(year, verbose=verbose)

    if not sessions:
        console.print("[yellow]No sessions found for {year}.[/yellow]")
        return

    console.print(f"\n[green]Found {len(sessions)} total sessions![/green]\n")

    # Compute stats
    stats = aggregate_stats(sessions, year)

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
