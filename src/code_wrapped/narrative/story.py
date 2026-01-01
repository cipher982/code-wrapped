"""Story context compilation for narrative generation.

Prepares structured context from stats for LLM narrative generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..stats import WrappedStats
    from ..enrichment.awards import Award


@dataclass
class NarrativeContext:
    """Structured context for LLM narrative generation."""

    # Core stats
    year: int
    total_sessions: int
    total_turns: int
    total_tokens: int
    total_hours: float
    active_days: int
    longest_streak_days: int

    # Agent breakdown
    primary_agent: str
    primary_agent_percentage: float
    agent_distribution: dict[str, float]

    # Patterns
    favorite_topic: str | None
    favorite_topic_percentage: float
    dominant_vibe: str | None
    dominant_vibe_percentage: float
    coding_archetype: str | None
    archetype_percentage: float

    # Time patterns
    peak_hour: int
    peak_hour_12h: str  # "2:00 AM" format
    is_night_owl: bool
    is_early_bird: bool
    weekend_percentage: float

    # Records
    longest_session_hours: float
    longest_session_topic: str | None
    most_active_day: str
    most_active_day_sessions: int
    busiest_month: str | None

    # Tool usage
    tool_personality: str | None
    dominant_tool: str | None
    dominant_tool_percentage: float

    # Repository stats
    top_repo: str | None
    repo_count: int

    # Awards (for narrative context)
    award_ids: list[str]
    award_count: int

    def to_prompt_string(self) -> str:
        """Format context as a clean string for LLM prompts."""
        lines = [
            f"Year: {self.year}",
            f"Total sessions: {self.total_sessions:,}",
            f"Total conversation turns: {self.total_turns:,}",
            f"Total hours: {self.total_hours:.1f}",
            f"Active days: {self.active_days}",
            f"Longest streak: {self.longest_streak_days} days",
            "",
            f"Primary agent: {self.primary_agent} ({self.primary_agent_percentage:.0f}%)",
            f"Agent split: {', '.join(f'{k} {v:.0f}%' for k, v in self.agent_distribution.items())}",
            "",
        ]

        if self.favorite_topic:
            lines.append(
                f"Favorite topic: {self.favorite_topic} ({self.favorite_topic_percentage:.0f}%)"
            )

        if self.dominant_vibe:
            lines.append(
                f"Dominant vibe: {self.dominant_vibe} ({self.dominant_vibe_percentage:.0f}%)"
            )

        if self.coding_archetype:
            lines.append(
                f"Coding archetype: {self.coding_archetype} ({self.archetype_percentage:.0f}%)"
            )

        lines.extend(
            [
                "",
                f"Peak hour: {self.peak_hour_12h}",
                f"Night owl: {self.is_night_owl}",
                f"Early bird: {self.is_early_bird}",
                f"Weekend coding: {self.weekend_percentage:.0f}%",
                "",
                f"Longest session: {self.longest_session_hours:.1f} hours",
                f"Most active day: {self.most_active_day} ({self.most_active_day_sessions} sessions)",
            ]
        )

        if self.busiest_month:
            lines.append(f"Busiest month: {self.busiest_month}")

        if self.tool_personality:
            lines.append(f"Tool personality: {self.tool_personality}")

        if self.dominant_tool:
            lines.append(
                f"Dominant tool: {self.dominant_tool} ({self.dominant_tool_percentage:.0f}%)"
            )

        if self.top_repo:
            lines.append(f"Top repository: {self.top_repo}")

        lines.append(f"Total repositories: {self.repo_count}")
        lines.append(f"Awards earned: {self.award_count} ({', '.join(self.award_ids)})")

        return "\n".join(lines)


def compile_narrative_context(
    stats: WrappedStats, awards: list[Award]
) -> NarrativeContext:
    """Compile narrative context from stats and awards.

    Args:
        stats: Aggregated stats
        awards: List of earned awards

    Returns:
        NarrativeContext with all data needed for narrative generation
    """
    from ..enrichment import (
        compute_archetype_profile,
        compute_fingerprint,
        get_dominant_vibe,
        get_top_topics,
    )

    # Agent distribution
    agent_dist = {}
    primary_agent = "Unknown"
    primary_pct = 0.0

    if stats.total_sessions > 0:
        for agent_type, agent_stats in stats.agent_stats.items():
            if agent_stats.session_count > 0:
                pct = (agent_stats.session_count / stats.total_sessions) * 100
                agent_dist[agent_type.value] = pct
                if pct > primary_pct:
                    primary_pct = pct
                    primary_agent = agent_type.value.title()

    # Topics
    top_topics = get_top_topics(stats.sessions, limit=1) if stats.sessions else []
    favorite_topic = top_topics[0][0] if top_topics else None
    favorite_topic_pct = top_topics[0][2] if top_topics else 0.0

    # Vibe
    vibe_result = get_dominant_vibe(stats.sessions) if stats.sessions else None
    dominant_vibe = vibe_result[0] if vibe_result else None
    vibe_pct = vibe_result[2] if vibe_result else 0.0

    # Archetype
    archetype_profile = (
        compute_archetype_profile(stats.sessions) if stats.sessions else None
    )
    archetype = archetype_profile.primary.display_name if archetype_profile else None
    archetype_pct = archetype_profile.primary.percentage if archetype_profile else 0.0

    # Time patterns
    hour = stats.peak_hour
    hour_12 = hour % 12 or 12
    am_pm = "AM" if hour < 12 else "PM"
    peak_hour_12h = f"{hour_12}:00 {am_pm}"

    is_night_owl = hour >= 22 or hour <= 4
    is_early_bird = 5 <= hour <= 8

    # Weekend percentage
    from datetime import datetime

    weekend_count = 0
    total_count = 0
    for date_str, count in stats.daily_sessions.items():
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            total_count += count
            if date.weekday() >= 5:
                weekend_count += count
        except ValueError:
            continue

    weekend_pct = (weekend_count / total_count * 100) if total_count > 0 else 0.0

    # Find busiest month
    month_counts: dict[str, int] = {}
    for date_str, count in stats.daily_sessions.items():
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date.strftime("%B")
            month_counts[month_key] = month_counts.get(month_key, 0) + count
        except ValueError:
            continue

    busiest_month = max(month_counts.items(), key=lambda x: x[1])[0] if month_counts else None

    # Tool fingerprint
    fingerprint = compute_fingerprint(stats.sessions) if stats.sessions else None
    tool_personality = fingerprint.personality if fingerprint else None
    dominant_tool = fingerprint.top_tools[0].name if fingerprint and fingerprint.top_tools else None
    dominant_tool_pct = (
        fingerprint.top_tools[0].percentage if fingerprint and fingerprint.top_tools else 0.0
    )

    # Longest session details
    longest_session_hours = 0.0
    longest_session_topic = None
    for agent_stats in stats.agent_stats.values():
        if agent_stats.longest_session_minutes > longest_session_hours * 60:
            longest_session_hours = agent_stats.longest_session_minutes / 60
            # Try to find the session for topic
            if stats.sessions and agent_stats.longest_session_id:
                for session in stats.sessions:
                    if session.id == agent_stats.longest_session_id:
                        # Get first user prompt as topic hint
                        if session.user_prompts:
                            longest_session_topic = session.user_prompts[0][:50]
                        break

    # Top repo
    top_repo = max(stats.all_repos.items(), key=lambda x: x[1])[0] if stats.all_repos else None

    return NarrativeContext(
        year=stats.year,
        total_sessions=stats.total_sessions,
        total_turns=stats.total_turns,
        total_tokens=stats.total_tokens,
        total_hours=stats.total_duration_minutes / 60,
        active_days=stats.active_days,
        longest_streak_days=stats.longest_streak_days,
        primary_agent=primary_agent,
        primary_agent_percentage=primary_pct,
        agent_distribution=agent_dist,
        favorite_topic=favorite_topic,
        favorite_topic_percentage=favorite_topic_pct,
        dominant_vibe=dominant_vibe,
        dominant_vibe_percentage=vibe_pct,
        coding_archetype=archetype,
        archetype_percentage=archetype_pct,
        peak_hour=stats.peak_hour,
        peak_hour_12h=peak_hour_12h,
        is_night_owl=is_night_owl,
        is_early_bird=is_early_bird,
        weekend_percentage=weekend_pct,
        longest_session_hours=longest_session_hours,
        longest_session_topic=longest_session_topic,
        most_active_day=stats.most_active_day or "Unknown",
        most_active_day_sessions=stats.most_active_day_sessions,
        busiest_month=busiest_month,
        tool_personality=tool_personality,
        dominant_tool=dominant_tool,
        dominant_tool_percentage=dominant_tool_pct,
        top_repo=top_repo,
        repo_count=len(stats.all_repos),
        award_ids=[award.id for award in awards],
        award_count=len(awards),
    )
