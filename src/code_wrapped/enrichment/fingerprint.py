"""Tool usage fingerprint analysis.

Creates a "Coding DNA" fingerprint based on how you use different tools.
Assigns personality labels based on tool usage patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parsers.base import Session

# Tool categories for fingerprinting
TOOL_CATEGORIES: dict[str, list[str]] = {
    "terminal": ["Bash", "bash", "shell", "cmd", "execute", "run"],
    "editor": ["Edit", "edit", "Write", "write", "NotebookEdit"],
    "reader": ["Read", "read", "Glob", "glob", "Grep", "grep", "search"],
    "browser": ["WebFetch", "web_fetch", "WebSearch", "browser", "playwright"],
    "ai_tools": ["Task", "TodoWrite", "AskUserQuestion", "agent"],
    "git": ["git", "commit", "push", "pull", "merge", "branch"],
}

# Personality labels based on dominant tool category
FINGERPRINT_PERSONALITIES: dict[str, tuple[str, str]] = {
    # category: (label, description)
    "terminal": ("Terminal Warrior", "You live in the command line"),
    "editor": ("Code Sculptor", "You craft code with precision"),
    "reader": ("Code Archaeologist", "You dig deep into codebases"),
    "browser": ("Research Hunter", "You hunt down information relentlessly"),
    "ai_tools": ("AI Orchestrator", "You delegate to AI agents effectively"),
    "git": ("Version Control Master", "You commit early and often"),
}

# Special combo fingerprints (require multiple categories)
COMBO_FINGERPRINTS: list[tuple[set[str], str, str]] = [
    # (required_categories, label, description)
    (
        {"terminal", "editor"},
        "Full-Stack Developer",
        "You balance terminal and editor work",
    ),
    (
        {"reader", "editor"},
        "Refactoring Expert",
        "You read deeply before changing carefully",
    ),
    (
        {"terminal", "ai_tools"},
        "Automation Architect",
        "You automate everything with AI assistance",
    ),
]


@dataclass
class ToolUsage:
    """Usage statistics for a single tool."""

    name: str
    count: int
    percentage: float


@dataclass
class CategoryUsage:
    """Usage statistics for a tool category."""

    category: str
    count: int
    percentage: float
    tools: list[ToolUsage]


@dataclass
class Fingerprint:
    """Complete tool usage fingerprint."""

    personality: str
    personality_description: str
    categories: list[CategoryUsage]
    top_tools: list[ToolUsage]
    total_tool_uses: int

    # Raw tool counts for visualization
    raw_counts: dict[str, int]


def categorize_tool(tool_name: str) -> str | None:
    """Map a tool name to its category.

    Returns:
        Category name or None if uncategorized
    """
    tool_lower = tool_name.lower()

    for category, keywords in TOOL_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in tool_lower:
                return category

    return None


def compute_fingerprint(sessions: list[Session]) -> Fingerprint | None:
    """Compute tool usage fingerprint from all sessions.

    Returns:
        Fingerprint with personality and usage breakdown
    """
    # Aggregate tool usage
    tool_counts: dict[str, int] = {}
    for session in sessions:
        for tool, count in session.tools_used.items():
            tool_counts[tool] = tool_counts.get(tool, 0) + count

    if not tool_counts:
        return None

    total = sum(tool_counts.values())

    # Compute category totals
    category_counts: dict[str, int] = {}
    category_tools: dict[str, dict[str, int]] = {}

    for tool, count in tool_counts.items():
        category = categorize_tool(tool)
        if category:
            category_counts[category] = category_counts.get(category, 0) + count
            if category not in category_tools:
                category_tools[category] = {}
            category_tools[category][tool] = count

    # Build category usage objects
    categories: list[CategoryUsage] = []
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        tools = [
            ToolUsage(
                name=t,
                count=c,
                percentage=(c / total) * 100,
            )
            for t, c in sorted(category_tools[category].items(), key=lambda x: x[1], reverse=True)
        ]
        categories.append(
            CategoryUsage(
                category=category,
                count=count,
                percentage=(count / total) * 100 if total > 0 else 0,
                tools=tools,
            )
        )

    # Build top tools list
    top_tools = [
        ToolUsage(
            name=t,
            count=c,
            percentage=(c / total) * 100,
        )
        for t, c in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # Determine personality
    personality = "Code Crafter"
    personality_description = "You use a balanced mix of tools"

    # Check combo fingerprints first
    top_categories = {cat.category for cat in categories[:3]}
    for required, label, desc in COMBO_FINGERPRINTS:
        if required.issubset(top_categories):
            personality = label
            personality_description = desc
            break
    else:
        # Fall back to dominant category
        if categories:
            dominant = categories[0].category
            if dominant in FINGERPRINT_PERSONALITIES:
                personality, personality_description = FINGERPRINT_PERSONALITIES[dominant]

    return Fingerprint(
        personality=personality,
        personality_description=personality_description,
        categories=categories,
        top_tools=top_tools,
        total_tool_uses=total,
        raw_counts=tool_counts,
    )


def get_fingerprint_ascii(fingerprint: Fingerprint, width: int = 40) -> str:
    """Generate ASCII bar chart of tool fingerprint.

    Returns:
        Multi-line string with ASCII bars
    """
    if not fingerprint.top_tools:
        return "No tool usage data"

    lines = [f"Your Coding DNA: {fingerprint.personality}", ""]

    max_count = max(t.count for t in fingerprint.top_tools[:6])
    bar_width = width - 15  # Leave room for label and percentage

    for tool in fingerprint.top_tools[:6]:
        bar_len = int((tool.count / max_count) * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        label = tool.name[:10].ljust(10)
        lines.append(f"  {label} {bar} {tool.percentage:4.1f}%")

    return "\n".join(lines)


def get_agent_fingerprints(
    sessions: list[Session],
) -> dict[str, Fingerprint]:
    """Compute fingerprints per agent.

    Returns:
        Dict mapping agent name to Fingerprint
    """
    from ..parsers.base import AgentType

    # Group sessions by agent
    agent_sessions: dict[str, list[Session]] = {}
    for session in sessions:
        agent_name = session.agent.value
        if agent_name not in agent_sessions:
            agent_sessions[agent_name] = []
        agent_sessions[agent_name].append(session)

    # Compute fingerprint per agent
    fingerprints = {}
    for agent_name, agent_sess in agent_sessions.items():
        fp = compute_fingerprint(agent_sess)
        if fp:
            fingerprints[agent_name] = fp

    return fingerprints
