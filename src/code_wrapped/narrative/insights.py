"""LLM-generated narrative insights.

Uses the Anthropic API to generate personalized, playful narratives
from coding statistics. Gracefully handles missing API keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .story import NarrativeContext


@dataclass
class Insights:
    """LLM-generated narrative insights."""

    headline: str  # "You had 847 conversations with AI this year"
    vibe_description: str  # "Your year was a balance of flow and exploration..."
    surprising_insight: str  # "You're most productive at 2AM - true night owl"
    epic_moment: str  # "Your longest session: 4.2 hours debugging OAuth"
    year_summary: str  # Full paragraph summarizing the year
    personal_note: str  # Closing personal reflection

    @property
    def full_narrative(self) -> str:
        """Combine all insights into a single narrative."""
        return (
            f"{self.headline}\n\n"
            f"{self.year_summary}\n\n"
            f"{self.vibe_description}\n\n"
            f"{self.surprising_insight}\n\n"
            f"{self.epic_moment}\n\n"
            f"{self.personal_note}"
        )


def _check_api_key() -> str | None:
    """Check for Anthropic API key in environment.

    Returns:
        API key if found, None otherwise
    """
    return os.getenv("ANTHROPIC_API_KEY")


def generate_insights(context: NarrativeContext) -> Insights | None:
    """Generate LLM-powered narrative insights.

    Args:
        context: NarrativeContext with all stats

    Returns:
        Insights object with generated narratives, or None if API unavailable
    """
    api_key = _check_api_key()
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        # anthropic package not installed
        return None

    client = anthropic.Anthropic(api_key=api_key)

    # Prepare context for LLM
    context_str = context.to_prompt_string()

    # System prompt
    system_prompt = """You are a creative writer crafting a "Spotify Wrapped" style year-in-review for a software developer. Your goal is to make their coding statistics feel personal, surprising, and celebratory.

Guidelines:
- Be playful and slightly witty, but not cheesy
- Focus on what makes THEIR year unique (not generic developer tropes)
- Highlight surprising patterns and outliers
- Make numbers feel impressive (use comparisons, metaphors)
- End on an encouraging, forward-looking note
- Keep each section concise (1-3 sentences)
"""

    # User prompt
    user_prompt = f"""Based on these coding statistics, generate a personalized year-in-review narrative:

{context_str}

Generate the following sections:

1. HEADLINE: A single impactful sentence that captures their year in one big number or pattern. Make it sound impressive.

2. YEAR_SUMMARY: A 2-3 sentence overview of their coding year. What defined it? What stands out?

3. VIBE_DESCRIPTION: 2-3 sentences describing their coding personality based on their dominant vibe and archetype. Be specific to their patterns.

4. SURPRISING_INSIGHT: 1-2 sentences highlighting the most unexpected or interesting pattern in their data. Something they might not have noticed.

5. EPIC_MOMENT: 1-2 sentences celebrating their most impressive stat (longest session, biggest streak, etc.). Make them feel accomplished.

6. PERSONAL_NOTE: A brief, encouraging closing thought that looks forward to next year. Personal and warm.

Format your response as:

HEADLINE:
[your headline]

YEAR_SUMMARY:
[your summary]

VIBE_DESCRIPTION:
[your vibe description]

SURPRISING_INSIGHT:
[your insight]

EPIC_MOMENT:
[your epic moment]

PERSONAL_NOTE:
[your note]
"""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.8,  # More creative
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse response
        content = response.content[0].text if response.content else ""
        sections = _parse_narrative_response(content)

        return Insights(
            headline=sections.get("HEADLINE", "Your coding year was remarkable"),
            year_summary=sections.get("YEAR_SUMMARY", "You coded a lot this year."),
            vibe_description=sections.get(
                "VIBE_DESCRIPTION", "Your coding style is unique."
            ),
            surprising_insight=sections.get(
                "SURPRISING_INSIGHT", "You have interesting patterns."
            ),
            epic_moment=sections.get("EPIC_MOMENT", "You had some great sessions."),
            personal_note=sections.get(
                "PERSONAL_NOTE", "Here's to another great year of coding!"
            ),
        )

    except Exception:
        # Gracefully handle any API errors
        return None


def _parse_narrative_response(content: str) -> dict[str, str]:
    """Parse LLM response into sections.

    Args:
        content: Raw LLM response text

    Returns:
        Dict mapping section names to content
    """
    sections = {}
    current_section = None
    current_content: list[str] = []

    for line in content.split("\n"):
        line = line.strip()

        # Check if this is a section header
        if line.endswith(":") and line[:-1].isupper():
            # Save previous section
            if current_section and current_content:
                sections[current_section] = "\n".join(current_content).strip()

            # Start new section
            current_section = line[:-1]
            current_content = []
        elif current_section and line:
            current_content.append(line)

    # Save last section
    if current_section and current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def generate_award_flavor_text(
    award_name: str, award_detail: str, context: NarrativeContext
) -> str | None:
    """Generate playful flavor text for an award.

    Args:
        award_name: Name of the award
        award_detail: Detail text for the award
        context: Full narrative context

    Returns:
        Enhanced description, or None if API unavailable
    """
    api_key = _check_api_key()
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Write a single playful sentence (15-25 words) celebrating this coding achievement:

Award: {award_name}
Detail: {award_detail}

Make it personal and slightly witty. Don't just repeat the detail."""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip() if response.content else None

    except Exception:
        return None
