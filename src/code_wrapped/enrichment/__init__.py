"""ML enrichment modules for Code Wrapped.

MVP: Keyword-based analysis
Phase 2: Embeddings + ML clustering
"""

from .archetypes import (
    ArchetypeProfile,
    ArchetypeScore,
    classify_prompt,
    compute_archetype_profile,
    get_archetype_summary,
)
from .awards import Award, detect_awards, get_most_active_day_award, get_peak_hour_award
from .fingerprint import (
    CategoryUsage,
    Fingerprint,
    ToolUsage,
    compute_fingerprint,
    get_agent_fingerprints,
    get_fingerprint_ascii,
)
from .topics import (
    TopicMatch,
    compute_topic_distribution,
    detect_session_topic,
    detect_topic,
    get_top_topics,
)
from .vibes import (
    VibeMatch,
    compute_vibe_distribution,
    detect_session_vibe,
    detect_vibe,
    get_dominant_vibe,
)

__all__ = [
    # Topics
    "TopicMatch",
    "detect_topic",
    "detect_session_topic",
    "compute_topic_distribution",
    "get_top_topics",
    # Vibes
    "VibeMatch",
    "detect_vibe",
    "detect_session_vibe",
    "compute_vibe_distribution",
    "get_dominant_vibe",
    # Archetypes
    "ArchetypeScore",
    "ArchetypeProfile",
    "classify_prompt",
    "compute_archetype_profile",
    "get_archetype_summary",
    # Fingerprint
    "ToolUsage",
    "CategoryUsage",
    "Fingerprint",
    "compute_fingerprint",
    "get_fingerprint_ascii",
    "get_agent_fingerprints",
    # Awards
    "Award",
    "detect_awards",
    "get_most_active_day_award",
    "get_peak_hour_award",
]
