"""Topic detection for sessions using keyword matching and TF-IDF.

MVP approach: Pattern matching + simple TF-IDF for clustering.
Phase 2 upgrade: Embeddings + KMeans for semantic clustering.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parsers.base import Session

# Topic keywords - each topic has multiple associated terms
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "api_integration": [
        "api",
        "endpoint",
        "rest",
        "graphql",
        "fetch",
        "request",
        "response",
        "webhook",
        "oauth",
        "authentication",
        "bearer",
        "token",
    ],
    "frontend": [
        "react",
        "vue",
        "svelte",
        "component",
        "css",
        "tailwind",
        "html",
        "dom",
        "ui",
        "ux",
        "layout",
        "responsive",
        "animation",
    ],
    "backend": [
        "server",
        "express",
        "fastapi",
        "flask",
        "django",
        "database",
        "sql",
        "postgres",
        "mongodb",
        "redis",
        "cache",
    ],
    "devops": [
        "docker",
        "kubernetes",
        "k8s",
        "deploy",
        "ci",
        "cd",
        "pipeline",
        "terraform",
        "aws",
        "gcp",
        "azure",
        "nginx",
        "coolify",
    ],
    "testing": [
        "test",
        "pytest",
        "jest",
        "unittest",
        "coverage",
        "mock",
        "fixture",
        "e2e",
        "integration",
        "unit",
    ],
    "ai_ml": [
        "ai",
        "ml",
        "model",
        "llm",
        "gpt",
        "claude",
        "embedding",
        "vector",
        "transformer",
        "neural",
        "training",
        "inference",
        "prompt",
    ],
    "data": [
        "data",
        "pandas",
        "numpy",
        "dataframe",
        "csv",
        "json",
        "parse",
        "transform",
        "etl",
        "analytics",
    ],
    "security": [
        "security",
        "auth",
        "encrypt",
        "hash",
        "password",
        "jwt",
        "cors",
        "xss",
        "sql injection",
        "vulnerability",
    ],
    "refactoring": [
        "refactor",
        "clean",
        "organize",
        "structure",
        "pattern",
        "abstract",
        "modular",
        "simplify",
    ],
    "debugging": [
        "debug",
        "error",
        "fix",
        "bug",
        "issue",
        "broken",
        "crash",
        "exception",
        "traceback",
        "stack",
    ],
    "documentation": [
        "doc",
        "readme",
        "comment",
        "docstring",
        "api doc",
        "spec",
        "markdown",
    ],
    "cli_tooling": [
        "cli",
        "command",
        "argparse",
        "click",
        "terminal",
        "shell",
        "script",
        "automation",
    ],
    "mobile": [
        "mobile",
        "ios",
        "android",
        "react native",
        "flutter",
        "swift",
        "kotlin",
        "app",
    ],
    "performance": [
        "performance",
        "optimize",
        "speed",
        "latency",
        "memory",
        "profile",
        "benchmark",
        "cache",
    ],
}

# Display names for topics (more human-friendly)
TOPIC_DISPLAY_NAMES: dict[str, str] = {
    "api_integration": "API Integrations",
    "frontend": "Frontend Development",
    "backend": "Backend Systems",
    "devops": "DevOps & Infrastructure",
    "testing": "Testing & QA",
    "ai_ml": "AI & Machine Learning",
    "data": "Data Processing",
    "security": "Security",
    "refactoring": "Refactoring",
    "debugging": "Debugging",
    "documentation": "Documentation",
    "cli_tooling": "CLI & Tooling",
    "mobile": "Mobile Development",
    "performance": "Performance",
}


@dataclass
class TopicMatch:
    """A detected topic with confidence score."""

    topic: str
    display_name: str
    score: float  # 0.0 to 1.0
    matched_keywords: list[str]


def detect_topic(text: str) -> TopicMatch | None:
    """Detect the primary topic from text using keyword matching.

    Args:
        text: The text to analyze (usually concatenated prompts)

    Returns:
        TopicMatch with highest confidence, or None if no match
    """
    if not text:
        return None

    text_lower = text.lower()
    topic_scores: dict[str, tuple[float, list[str]]] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        matched = []
        for keyword in keywords:
            # Use word boundary matching to avoid partial matches
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text_lower):
                matched.append(keyword)

        if matched:
            # Score = number of matched keywords / total keywords for topic
            # Weighted by total matches to favor topics with more evidence
            score = len(matched) / len(keywords)
            topic_scores[topic] = (score, matched)

    if not topic_scores:
        return None

    # Get topic with highest score
    best_topic = max(topic_scores.items(), key=lambda x: (x[1][0], len(x[1][1])))
    topic_id = best_topic[0]
    score, matched = best_topic[1]

    return TopicMatch(
        topic=topic_id,
        display_name=TOPIC_DISPLAY_NAMES.get(topic_id, topic_id.replace("_", " ").title()),
        score=score,
        matched_keywords=matched,
    )


def detect_session_topic(session: Session) -> TopicMatch | None:
    """Detect topic from a session's prompts and repo name.

    Args:
        session: Session object with user_prompts and repo

    Returns:
        TopicMatch or None
    """
    # Combine prompts and repo name for analysis
    text_parts = session.user_prompts.copy()
    if session.repo:
        text_parts.append(session.repo)

    combined_text = " ".join(text_parts)
    return detect_topic(combined_text)


def compute_topic_distribution(sessions: list[Session]) -> dict[str, int]:
    """Compute topic distribution across all sessions.

    Returns:
        Dict mapping topic display names to session counts
    """
    topic_counts: dict[str, int] = defaultdict(int)

    for session in sessions:
        topic = detect_session_topic(session)
        if topic:
            topic_counts[topic.display_name] += 1
        else:
            topic_counts["Other"] += 1

    return dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True))


def get_top_topics(sessions: list[Session], limit: int = 5) -> list[tuple[str, int, float]]:
    """Get top topics with counts and percentages.

    Returns:
        List of (topic_name, count, percentage) tuples
    """
    distribution = compute_topic_distribution(sessions)
    total = sum(distribution.values())

    if total == 0:
        return []

    results = []
    for topic, count in list(distribution.items())[:limit]:
        percentage = (count / total) * 100
        results.append((topic, count, percentage))

    return results
