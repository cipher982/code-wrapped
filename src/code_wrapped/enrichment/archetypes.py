"""Prompt archetype classifier.

Categorizes user prompts into personality types based on their intent:
- Architect: System design and structure
- Debugger: Bug fixing and troubleshooting
- Explorer: Learning and understanding
- Builder: Creating new features
- Shipper: Deployment and releases
- Tester: Testing and validation
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parsers.base import Session

# Archetype keywords - first match wins, so order matters within each archetype
ARCHETYPE_PATTERNS: dict[str, list[str]] = {
    "architect": [
        "design",
        "architecture",
        "structure",
        "refactor",
        "organize",
        "pattern",
        "abstraction",
        "interface",
        "module",
        "clean up",
        "restructure",
        "simplify",
        "split",
        "extract",
        "decouple",
    ],
    "debugger": [
        "fix",
        "error",
        "bug",
        "not working",
        "broken",
        "why",
        "issue",
        "crash",
        "fail",
        "doesn't",
        "won't",
        "can't",
        "problem",
        "wrong",
        "debug",
        "investigate",
    ],
    "explorer": [
        "how",
        "what",
        "explain",
        "understand",
        "learn",
        "why does",
        "what is",
        "show me",
        "example",
        "documentation",
        "tutorial",
        "help me understand",
    ],
    "builder": [
        "add",
        "create",
        "implement",
        "build",
        "new feature",
        "make",
        "write",
        "generate",
        "setup",
        "configure",
        "install",
        "integrate",
    ],
    "shipper": [
        "deploy",
        "release",
        "push",
        "publish",
        "ship",
        "merge",
        "production",
        "launch",
        "rollout",
        "ci",
        "cd",
        "pipeline",
    ],
    "tester": [
        "test",
        "verify",
        "check",
        "validate",
        "coverage",
        "assert",
        "expect",
        "mock",
        "fixture",
        "e2e",
        "integration test",
        "unit test",
    ],
}

# Display info for each archetype
ARCHETYPE_DISPLAY: dict[str, tuple[str, str, str]] = {
    # archetype: (display_name, emoji, description)
    "architect": ("The Architect", "🏛️", "You think in systems and structures"),
    "debugger": ("The Debugger", "🔧", "You hunt bugs with precision"),
    "explorer": ("The Explorer", "🧭", "You're always learning something new"),
    "builder": ("The Builder", "🔨", "You create features at full speed"),
    "shipper": ("The Shipper", "🚀", "You get things to production"),
    "tester": ("The Tester", "🧪", "You ensure quality before shipping"),
}


@dataclass
class ArchetypeScore:
    """Score for a single archetype."""

    archetype: str
    display_name: str
    emoji: str
    description: str
    count: int
    percentage: float


@dataclass
class ArchetypeProfile:
    """Full archetype profile for a user."""

    primary: ArchetypeScore
    secondary: ArchetypeScore | None
    all_scores: list[ArchetypeScore]
    total_classified: int
    total_prompts: int


def classify_prompt(text: str) -> str | None:
    """Classify a single prompt into an archetype.

    Args:
        text: The prompt text

    Returns:
        Archetype name or None if unclassified
    """
    if not text:
        return None

    text_lower = text.lower()

    # Score each archetype
    archetype_scores: dict[str, int] = defaultdict(int)

    for archetype, patterns in ARCHETYPE_PATTERNS.items():
        for pattern in patterns:
            if " " in pattern:
                # Multi-word phrase
                if pattern in text_lower:
                    archetype_scores[archetype] += 2  # Phrases worth more
            else:
                # Single word with word boundaries
                regex = rf"\b{re.escape(pattern)}\b"
                matches = len(re.findall(regex, text_lower))
                archetype_scores[archetype] += matches

    if not archetype_scores:
        return None

    # Return archetype with highest score
    best = max(archetype_scores.items(), key=lambda x: x[1])
    if best[1] > 0:
        return best[0]

    return None


def classify_session_prompts(session: Session) -> dict[str, int]:
    """Classify all prompts in a session.

    Returns:
        Dict mapping archetype names to counts
    """
    counts: dict[str, int] = defaultdict(int)

    for prompt in session.user_prompts:
        archetype = classify_prompt(prompt)
        if archetype:
            counts[archetype] += 1

    return dict(counts)


def compute_archetype_profile(sessions: list[Session]) -> ArchetypeProfile | None:
    """Compute full archetype profile from all sessions.

    Returns:
        ArchetypeProfile with primary, secondary, and all archetype scores
    """
    # Aggregate counts across all sessions
    total_counts: dict[str, int] = defaultdict(int)
    total_prompts = 0

    for session in sessions:
        total_prompts += len(session.user_prompts)
        session_counts = classify_session_prompts(session)
        for archetype, count in session_counts.items():
            total_counts[archetype] += count

    if not total_counts:
        return None

    total_classified = sum(total_counts.values())

    # Build scores list
    all_scores: list[ArchetypeScore] = []
    for archetype, count in sorted(total_counts.items(), key=lambda x: x[1], reverse=True):
        display_name, emoji, description = ARCHETYPE_DISPLAY.get(
            archetype, (archetype.title(), "🎯", "")
        )
        percentage = (count / total_classified) * 100 if total_classified > 0 else 0
        all_scores.append(
            ArchetypeScore(
                archetype=archetype,
                display_name=display_name,
                emoji=emoji,
                description=description,
                count=count,
                percentage=percentage,
            )
        )

    if not all_scores:
        return None

    return ArchetypeProfile(
        primary=all_scores[0],
        secondary=all_scores[1] if len(all_scores) > 1 else None,
        all_scores=all_scores,
        total_classified=total_classified,
        total_prompts=total_prompts,
    )


def get_archetype_summary(sessions: list[Session]) -> str:
    """Get a human-readable archetype summary.

    Returns:
        String like "You're 45% Debugger, 30% Builder, 15% Architect..."
    """
    profile = compute_archetype_profile(sessions)
    if not profile:
        return "Not enough data to determine your coding archetype."

    parts = []
    for score in profile.all_scores[:4]:  # Top 4 archetypes
        parts.append(f"{score.percentage:.0f}% {score.display_name}")

    return "You're " + ", ".join(parts)
