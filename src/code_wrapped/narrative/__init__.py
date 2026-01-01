"""Narrative generation for Code Wrapped.

This module provides LLM-powered narrative generation to create
personalized, "Spotify Wrapped"-style stories from coding statistics.
"""

from .insights import generate_insights, Insights
from .story import compile_narrative_context, NarrativeContext

__all__ = [
    "generate_insights",
    "Insights",
    "compile_narrative_context",
    "NarrativeContext",
]
