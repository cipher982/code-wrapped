"""Awards and superlatives detection.

Automatically detects award-worthy patterns in session data.
Awards are based on statistical outliers and notable patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..stats import WrappedStats

# Award types are documented inline in detect_awards() function
# 12 award types: night_owl, early_bird, bug_slayer, marathon_coder, speed_demon,
# streak_master, repo_hopper, deep_diver, ai_whisperer, polyglot, weekend_warrior, terminal_master


@dataclass
class Award:
    """A earned award with context."""

    id: str
    name: str
    emoji: str
    description: str
    detail: str  # Specific context, e.g., "Your longest session: 4h 23m"
    value: float | int | str  # The qualifying value


def detect_awards(stats: WrappedStats) -> list[Award]:
    """Detect all qualifying awards from stats.

    Args:
        stats: WrappedStats with all aggregated data

    Returns:
        List of Award objects earned
    """
    awards: list[Award] = []

    # Night Owl: Peak hour between 11pm-4am
    late_night_hours = [23, 0, 1, 2, 3, 4]
    late_night_count = sum(
        stats.hours_distribution.get(h, 0) for h in late_night_hours
    )
    total_sessions = stats.total_sessions
    if total_sessions > 0 and late_night_count / total_sessions > 0.15:
        peak_late = max(
            late_night_hours,
            key=lambda h: stats.hours_distribution.get(h, 0),
        )
        awards.append(
            Award(
                id="night_owl",
                name="Night Owl",
                emoji="🦉",
                description="Peak coding after midnight",
                detail=f"Your peak late-night hour: {peak_late}:00",
                value=late_night_count,
            )
        )

    # Early Bird: Peak hour between 5am-8am
    early_hours = [5, 6, 7, 8]
    early_count = sum(stats.hours_distribution.get(h, 0) for h in early_hours)
    if total_sessions > 0 and early_count / total_sessions > 0.15:
        awards.append(
            Award(
                id="early_bird",
                name="Early Bird",
                emoji="🐦",
                description="Gets the worm before dawn",
                detail=f"{early_count} sessions before 9am",
                value=early_count,
            )
        )

    # Marathon Coder: Longest session > 3 hours
    for agent, agent_stats in stats.agent_stats.items():
        if agent_stats.longest_session_minutes > 180:  # 3 hours
            hours = agent_stats.longest_session_minutes / 60
            awards.append(
                Award(
                    id="marathon_coder",
                    name="Marathon Coder",
                    emoji="🏃",
                    description="Your longest session was epic",
                    detail=f"Longest session: {hours:.1f} hours on {agent.value}",
                    value=hours,
                )
            )
            break  # Only award once

    # Streak Master: 30+ day streak
    if stats.longest_streak_days >= 30:
        awards.append(
            Award(
                id="streak_master",
                name="Streak Master",
                emoji="🔥",
                description="Consistency is your superpower",
                detail=f"{stats.longest_streak_days}-day coding streak",
                value=stats.longest_streak_days,
            )
        )

    # Repo Hopper: 10+ repos
    repo_count = len(stats.all_repos)
    if repo_count >= 10:
        awards.append(
            Award(
                id="repo_hopper",
                name="Repo Hopper",
                emoji="🐰",
                description="You bounced between many projects",
                detail=f"Worked across {repo_count} repositories",
                value=repo_count,
            )
        )

    # Deep Diver: Avg turns > 50
    avg_turns = stats.total_turns / total_sessions if total_sessions > 0 else 0
    if avg_turns > 50:
        awards.append(
            Award(
                id="deep_diver",
                name="Deep Diver",
                emoji="🤿",
                description="Your conversations go deep",
                detail=f"Average {avg_turns:.0f} turns per session",
                value=avg_turns,
            )
        )

    # AI Whisperer: High token usage
    if stats.total_tokens > 500_000_000:  # 500M tokens
        billions = stats.total_tokens / 1_000_000_000
        awards.append(
            Award(
                id="ai_whisperer",
                name="AI Whisperer",
                emoji="🧙",
                description="You consumed serious AI power",
                detail=f"{billions:.1f} billion tokens consumed",
                value=stats.total_tokens,
            )
        )

    # Polyglot: Used 3+ agents
    agents_used = len([a for a, s in stats.agent_stats.items() if s.session_count > 0])
    if agents_used >= 3:
        awards.append(
            Award(
                id="polyglot",
                name="Polyglot",
                emoji="🌍",
                description="Master of multiple agents",
                detail=f"Used {agents_used} different AI agents",
                value=agents_used,
            )
        )

    # Weekend Warrior: High weekend ratio
    weekend_count = 0
    weekday_count = 0
    for date_str, count in stats.daily_sessions.items():
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                weekend_count += count
            else:
                weekday_count += count
        except ValueError:
            continue

    if weekend_count + weekday_count > 0:
        weekend_ratio = weekend_count / (weekend_count + weekday_count)
        if weekend_ratio > 0.35:  # 35%+ on weekends (vs ~28% if uniform)
            awards.append(
                Award(
                    id="weekend_warrior",
                    name="Weekend Warrior",
                    emoji="⚔️",
                    description="Weekends are for coding",
                    detail=f"{weekend_ratio * 100:.0f}% of sessions on weekends",
                    value=weekend_ratio,
                )
            )

    # Terminal Master: Bash > 50%
    total_tools = sum(stats.all_tools.values())
    bash_count = stats.all_tools.get("Bash", 0) + stats.all_tools.get("bash", 0)
    if total_tools > 0 and bash_count / total_tools > 0.5:
        awards.append(
            Award(
                id="terminal_master",
                name="Terminal Master",
                emoji="💻",
                description="Command line is your home",
                detail=f"{bash_count / total_tools * 100:.0f}% Bash usage",
                value=bash_count / total_tools,
            )
        )

    # Bug Slayer: High ratio of debugging sessions (based on vibe detection)
    if stats.sessions:
        from .vibes import detect_session_vibe

        debugging_sessions = 0
        for session in stats.sessions:
            vibe = detect_session_vibe(session)
            if vibe and vibe.vibe == "debugging_hell":
                debugging_sessions += 1

        if total_sessions > 10 and debugging_sessions / total_sessions > 0.25:
            awards.append(
                Award(
                    id="bug_slayer",
                    name="Bug Slayer",
                    emoji="🗡️",
                    description="Hunted down bugs relentlessly",
                    detail=f"{debugging_sessions} debugging sessions ({debugging_sessions * 100 // total_sessions}%)",
                    value=debugging_sessions,
                )
            )

    # Speed Demon: Many fast, productive sessions
    if stats.sessions:
        fast_sessions = 0
        for session in stats.sessions:
            # Fast = under 15 minutes but at least 5 turns (not trivial)
            if session.duration_minutes < 15 and session.turn_count >= 5:
                fast_sessions += 1

        if total_sessions > 20 and fast_sessions / total_sessions > 0.3:
            awards.append(
                Award(
                    id="speed_demon",
                    name="Speed Demon",
                    emoji="⚡",
                    description="Fast, focused sessions",
                    detail=f"{fast_sessions} sessions under 15 minutes ({fast_sessions * 100 // total_sessions}%)",
                    value=fast_sessions,
                )
            )

    return awards


def get_most_active_day_award(stats: WrappedStats) -> Award | None:
    """Generate award for most active day."""
    if not stats.most_active_day:
        return None

    try:
        date = datetime.strptime(stats.most_active_day, "%Y-%m-%d")
        day_name = date.strftime("%B %d")
    except ValueError:
        day_name = stats.most_active_day

    return Award(
        id="most_active_day",
        name="Your Biggest Day",
        emoji="📅",
        description="Most sessions in a single day",
        detail=f"{stats.most_active_day_sessions} sessions on {day_name}",
        value=stats.most_active_day_sessions,
    )


def get_peak_hour_award(stats: WrappedStats) -> Award | None:
    """Generate award for peak productivity hour."""
    if stats.peak_hour is None:
        return None

    hour = stats.peak_hour
    hour_12 = hour % 12 or 12
    am_pm = "AM" if hour < 12 else "PM"

    # Determine time category
    if 5 <= hour < 12:
        time_desc = "morning person"
    elif 12 <= hour < 17:
        time_desc = "afternoon coder"
    elif 17 <= hour < 21:
        time_desc = "evening developer"
    else:
        time_desc = "night coder"

    return Award(
        id="peak_hour",
        name="Peak Hour",
        emoji="⏰",
        description=f"You're a {time_desc}",
        detail=f"Most productive at {hour_12}:00 {am_pm}",
        value=hour,
    )
