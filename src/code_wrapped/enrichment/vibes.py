"""Vibe/sentiment detection for sessions.

Analyzes session content to determine the "mood" or "vibe" of coding sessions.
MVP approach: Keyword-based heuristics.
Phase 2: Sentiment classifier or LLM analysis.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parsers.base import Session

# Vibe keywords with weights (positive = strong indicator)
VIBE_PATTERNS: dict[str, dict[str, float]] = {
    "debugging_hell": {
        # Frustration signals
        "error": 1.0,
        "not working": 2.0,
        "why": 0.5,
        "wtf": 3.0,
        "broken": 1.5,
        "fail": 1.0,
        "crash": 1.5,
        "bug": 1.0,
        "issue": 0.5,
        "stuck": 2.0,
        "help": 1.0,
        "doesn't work": 2.0,
        "won't": 1.0,
        "can't": 0.5,
        "exception": 1.0,
        "traceback": 1.5,
        "undefined": 1.0,
        "null": 0.5,
        "none": 0.3,
    },
    "flow_state": {
        # Productivity signals
        "perfect": 2.0,
        "works": 1.0,
        "great": 1.5,
        "done": 1.0,
        "ship": 2.0,
        "deploy": 1.5,
        "finish": 1.0,
        "complete": 1.0,
        "success": 1.5,
        "awesome": 1.5,
        "nice": 0.5,
        "good": 0.3,
        "thanks": 0.5,
        "looks good": 1.5,
        "lgtm": 2.0,
        "merged": 1.5,
    },
    "exploration": {
        # Discovery signals
        "what if": 2.0,
        "could we": 1.5,
        "try": 1.0,
        "experiment": 2.0,
        "explore": 2.0,
        "maybe": 0.5,
        "possible": 0.5,
        "alternative": 1.0,
        "option": 0.5,
        "approach": 0.5,
        "idea": 1.0,
        "prototype": 1.5,
        "poc": 1.5,
        "spike": 1.5,
    },
    "learning": {
        # Learning signals
        "how do": 1.5,
        "how does": 1.5,
        "explain": 2.0,
        "understand": 1.5,
        "what is": 1.5,
        "why does": 1.5,
        "learn": 2.0,
        "tutorial": 1.5,
        "example": 1.0,
        "documentation": 1.0,
        "guide": 1.0,
        "newbie": 1.5,
        "beginner": 1.5,
        "first time": 1.5,
    },
    "deep_work": {
        # Deep concentration signals (inferred from session characteristics)
        "architecture": 1.5,
        "design": 1.0,
        "refactor": 1.5,
        "system": 0.5,
        "implement": 1.0,
        "build": 0.5,
        "complex": 1.0,
        "careful": 1.0,
        "think": 0.5,
        "plan": 1.0,
    },
}

# Display names and emojis for vibes
VIBE_DISPLAY: dict[str, tuple[str, str]] = {
    "debugging_hell": ("Debugging Hell", "🔥"),
    "flow_state": ("Flow State", "🌊"),
    "exploration": ("Exploration Mode", "🧭"),
    "learning": ("Learning Mode", "📚"),
    "deep_work": ("Deep Work", "🎯"),
}


@dataclass
class VibeMatch:
    """A detected vibe with confidence score."""

    vibe: str
    display_name: str
    emoji: str
    score: float  # Raw weighted score
    confidence: float  # Normalized 0.0 to 1.0


def detect_vibe(text: str) -> VibeMatch | None:
    """Detect the primary vibe from text.

    Args:
        text: Text to analyze (usually concatenated prompts)

    Returns:
        VibeMatch with highest score, or None if no match
    """
    if not text:
        return None

    text_lower = text.lower()
    vibe_scores: dict[str, float] = {}

    for vibe, patterns in VIBE_PATTERNS.items():
        total_score = 0.0

        for pattern, weight in patterns.items():
            # Use word boundary matching for single words
            if " " in pattern:
                # Multi-word phrases: exact match
                if pattern in text_lower:
                    total_score += weight
            else:
                # Single words: word boundary match
                regex = rf"\b{re.escape(pattern)}\b"
                matches = len(re.findall(regex, text_lower))
                total_score += weight * min(matches, 3)  # Cap at 3 matches per keyword

        if total_score > 0:
            vibe_scores[vibe] = total_score

    if not vibe_scores:
        return None

    # Get vibe with highest score
    best_vibe = max(vibe_scores.items(), key=lambda x: x[1])
    vibe_id, score = best_vibe

    # Normalize confidence (cap at 10 for full confidence)
    confidence = min(score / 10.0, 1.0)

    display_name, emoji = VIBE_DISPLAY.get(vibe_id, (vibe_id.replace("_", " ").title(), "🎯"))

    return VibeMatch(
        vibe=vibe_id,
        display_name=display_name,
        emoji=emoji,
        score=score,
        confidence=confidence,
    )


def detect_session_vibe(session: Session) -> VibeMatch | None:
    """Detect vibe from a session's prompts.

    Also considers session characteristics like duration and turn count.

    Args:
        session: Session object with user_prompts

    Returns:
        VibeMatch or None
    """
    combined_text = " ".join(session.user_prompts)
    vibe = detect_vibe(combined_text)

    # Adjust vibe based on session characteristics
    if vibe:
        # Long sessions with many turns suggest deep_work or debugging_hell
        if session.turn_count > 50 and session.duration_minutes > 60:
            if vibe.vibe == "debugging_hell":
                # Boost debugging confidence for long struggle sessions
                vibe = VibeMatch(
                    vibe=vibe.vibe,
                    display_name=vibe.display_name,
                    emoji=vibe.emoji,
                    score=vibe.score * 1.5,
                    confidence=min(vibe.confidence * 1.5, 1.0),
                )
            elif vibe.vibe not in ("debugging_hell", "deep_work"):
                # Consider as deep_work if not already debugging
                if vibe.score < 3:  # Low original confidence
                    return VibeMatch(
                        vibe="deep_work",
                        display_name="Deep Work",
                        emoji="🎯",
                        score=5.0,
                        confidence=0.5,
                    )

    return vibe


def compute_vibe_distribution(sessions: list[Session]) -> dict[str, int]:
    """Compute vibe distribution across all sessions.

    Returns:
        Dict mapping vibe display names to session counts
    """
    vibe_counts: dict[str, int] = defaultdict(int)

    for session in sessions:
        vibe = detect_session_vibe(session)
        if vibe:
            vibe_counts[vibe.display_name] += 1
        else:
            vibe_counts["Neutral"] += 1

    return dict(sorted(vibe_counts.items(), key=lambda x: x[1], reverse=True))


def get_dominant_vibe(sessions: list[Session]) -> tuple[str, str, float] | None:
    """Get the dominant vibe across all sessions.

    Returns:
        (display_name, emoji, percentage) or None
    """
    distribution = compute_vibe_distribution(sessions)
    total = sum(distribution.values())

    if total == 0:
        return None

    # Find dominant (excluding "Neutral" if there are other vibes)
    filtered = {k: v for k, v in distribution.items() if k != "Neutral"}
    if not filtered:
        filtered = distribution

    dominant_name = max(filtered.items(), key=lambda x: x[1])[0]
    count = filtered[dominant_name]
    percentage = (count / total) * 100

    # Look up emoji
    emoji = "🎯"
    for vibe_id, (display, e) in VIBE_DISPLAY.items():
        if display == dominant_name:
            emoji = e
            break

    return (dominant_name, emoji, percentage)
