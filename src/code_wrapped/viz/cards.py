"""PNG card generation for social sharing using Pillow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from ..stats import WrappedStats


# Card dimensions
CARD_WIDTH = 1200
CARD_HEIGHT = 630  # Twitter/OpenGraph optimal size

# Color palette
COLORS = {
    'background': '#0F1419',
    'primary': '#5436DA',
    'secondary': '#10A37F',
    'text': '#FFFFFF',
    'text_dim': '#8B98A5',
    'accent': '#FF6B6B',
}


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font for rendering text.

    Falls back to default font if custom fonts not available.

    Args:
        size: Font size
        bold: Whether to use bold weight

    Returns:
        ImageFont object
    """
    try:
        # Try to load system fonts
        if bold:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except Exception:
        # Fallback to default
        return ImageFont.load_default()


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string like '#FFFFFF'

    Returns:
        RGB tuple
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def draw_text_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    color: str,
    width: int = CARD_WIDTH,
) -> None:
    """Draw centered text at a given Y position.

    Args:
        draw: ImageDraw object
        text: Text to draw
        y: Y coordinate
        font: Font to use
        color: Color hex string
        width: Width of the canvas for centering
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill=hex_to_rgb(color))


def generate_hero_card(stats: WrappedStats) -> Image.Image:
    """Generate the hero stats card.

    Shows the big numbers: sessions, turns, hours, tokens.

    Args:
        stats: Wrapped statistics

    Returns:
        PIL Image object
    """
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=hex_to_rgb(COLORS['background']))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(80, bold=True)
    draw_text_centered(draw, f"Code Wrapped {stats.year}", 60, title_font, COLORS['text'])

    # Subtitle
    subtitle_font = get_font(30)
    draw_text_centered(draw, "Your AI Coding Year in Review", 160, subtitle_font, COLORS['text_dim'])

    # Stats grid
    stats_font = get_font(60, bold=True)
    label_font = get_font(24)

    stats_data = [
        (f"{stats.total_sessions:,}", "Sessions"),
        (f"{stats.total_turns:,}", "Conversation Turns"),
        (f"{stats.total_duration_minutes / 60:.0f}", "Hours Coding"),
    ]

    if stats.total_tokens > 0:
        # Format tokens nicely (e.g., 1.2B, 450M, 89K)
        tokens = stats.total_tokens
        if tokens >= 1_000_000_000:
            token_str = f"{tokens / 1_000_000_000:.1f}B"
        elif tokens >= 1_000_000:
            token_str = f"{tokens / 1_000_000:.0f}M"
        elif tokens >= 1_000:
            token_str = f"{tokens / 1_000:.0f}K"
        else:
            token_str = f"{tokens}"
        stats_data.append((token_str, "Tokens Consumed"))

    # Layout stats in a 2x2 grid
    grid_cols = 2
    grid_rows = (len(stats_data) + 1) // 2
    col_width = CARD_WIDTH // grid_cols
    start_y = 280
    row_height = 120

    for i, (value, label) in enumerate(stats_data):
        col = i % grid_cols
        row = i // grid_cols
        x = col * col_width + col_width // 2
        y = start_y + row * row_height

        # Draw value
        bbox = draw.textbbox((0, 0), value, font=stats_font)
        value_width = bbox[2] - bbox[0]
        draw.text((x - value_width // 2, y), value, font=stats_font, fill=hex_to_rgb(COLORS['primary']))

        # Draw label
        bbox = draw.textbbox((0, 0), label, font=label_font)
        label_width = bbox[2] - bbox[0]
        draw.text((x - label_width // 2, y + 70), label, font=label_font, fill=hex_to_rgb(COLORS['text_dim']))

    # Footer
    footer_font = get_font(20)
    draw_text_centered(draw, "Generated with code-wrapped", CARD_HEIGHT - 50, footer_font, COLORS['text_dim'])

    return img


def generate_tool_fingerprint_card(stats: WrappedStats, fingerprint: dict[str, Any]) -> Image.Image:
    """Generate the tool fingerprint card.

    Shows top tools used with percentages.

    Args:
        stats: Wrapped statistics
        fingerprint: Fingerprint data from enrichment

    Returns:
        PIL Image object
    """
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=hex_to_rgb(COLORS['background']))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(60, bold=True)
    draw_text_centered(draw, "Your Tool DNA", 60, title_font, COLORS['text'])

    # Personality
    personality = fingerprint.get('personality', 'Code Maestro')
    desc_font = get_font(28)
    draw_text_centered(draw, f'"{personality}"', 150, desc_font, COLORS['primary'])

    # Description
    description = fingerprint.get('description', '')
    if description:
        desc_small = get_font(22)
        # Wrap text if too long
        max_width = CARD_WIDTH - 100
        if len(description) > 80:
            description = description[:77] + "..."
        draw_text_centered(draw, description, 200, desc_small, COLORS['text_dim'])

    # Top tools
    top_tools = fingerprint.get('top_tools', [])[:5]
    if top_tools:
        tool_font = get_font(28)
        bar_start_y = 280
        bar_height = 50
        bar_spacing = 20
        bar_max_width = 800
        label_x = 180

        for i, tool in enumerate(top_tools):
            y = bar_start_y + i * (bar_height + bar_spacing)
            name = tool['name']
            percentage = tool['percentage']

            # Draw tool name
            draw.text((label_x, y + 10), name, font=tool_font, fill=hex_to_rgb(COLORS['text']))

            # Draw percentage bar
            bar_x = label_x + 200
            bar_width = int((percentage / 100) * bar_max_width)
            draw.rectangle(
                [bar_x, y + 5, bar_x + bar_width, y + bar_height - 5],
                fill=hex_to_rgb(COLORS['secondary']),
            )

            # Draw percentage text
            pct_text = f"{percentage:.1f}%"
            draw.text((bar_x + bar_width + 15, y + 10), pct_text, font=tool_font, fill=hex_to_rgb(COLORS['text']))

    return img


def generate_agent_comparison_card(stats: WrappedStats) -> Image.Image:
    """Generate agent comparison card.

    Shows which AI agents were used and how much.

    Args:
        stats: Wrapped statistics

    Returns:
        PIL Image object
    """
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=hex_to_rgb(COLORS['background']))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(60, bold=True)
    draw_text_centered(draw, "Your AI Partners", 60, title_font, COLORS['text'])

    # Subtitle
    subtitle_font = get_font(28)
    draw_text_centered(draw, "Which agents did you work with most?", 150, subtitle_font, COLORS['text_dim'])

    # Collect agent data
    agent_colors = {
        'claude': '#5436DA',
        'codex': '#10A37F',
        'cursor': '#000000',
        'gemini': '#4285F4',
    }

    agents_data = []
    for agent in ['claude', 'codex', 'cursor', 'gemini']:
        from ..parsers.base import AgentType
        agent_enum = AgentType(agent)
        agent_stats = stats.agent_stats.get(agent_enum)
        if agent_stats and agent_stats.session_count > 0:
            percentage = (agent_stats.session_count / stats.total_sessions) * 100
            agents_data.append({
                'name': agent.title(),
                'sessions': agent_stats.session_count,
                'percentage': percentage,
                'color': agent_colors.get(agent, COLORS['primary']),
            })

    # Sort by usage
    agents_data.sort(key=lambda x: x['sessions'], reverse=True)

    # Draw agent bars
    if agents_data:
        bar_start_y = 250
        bar_height = 70
        bar_spacing = 30
        bar_max_width = 700
        label_x = 220

        agent_font = get_font(32, bold=True)
        detail_font = get_font(24)

        for i, agent in enumerate(agents_data):
            y = bar_start_y + i * (bar_height + bar_spacing)

            # Draw agent name
            draw.text((label_x, y + 5), agent['name'], font=agent_font, fill=hex_to_rgb(COLORS['text']))

            # Draw bar
            bar_x = label_x + 150
            bar_width = int((agent['percentage'] / 100) * bar_max_width)
            draw.rectangle(
                [bar_x, y + 10, bar_x + bar_width, y + bar_height - 10],
                fill=hex_to_rgb(agent['color']),
            )

            # Draw stats
            stats_text = f"{agent['sessions']:,} sessions ({agent['percentage']:.1f}%)"
            draw.text((bar_x + 10, y + 20), stats_text, font=detail_font, fill=hex_to_rgb(COLORS['text']))

    return img


def generate_award_card(award_name: str, award_emoji: str, award_detail: str, year: int) -> Image.Image:
    """Generate an award card.

    Args:
        award_name: Name of the award
        award_emoji: Emoji for the award
        award_detail: Detail text
        year: Year

    Returns:
        PIL Image object
    """
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=hex_to_rgb(COLORS['background']))
    draw = ImageDraw.Draw(img)

    # Title
    title_font = get_font(50, bold=True)
    draw_text_centered(draw, f"Code Wrapped {year}", 50, title_font, COLORS['text'])

    # Award banner
    banner_font = get_font(35)
    draw_text_centered(draw, "YOU EARNED", 140, banner_font, COLORS['text_dim'])

    # Emoji (using text, as PIL doesn't natively support emoji rendering well)
    emoji_font = get_font(120)
    draw_text_centered(draw, award_emoji, 200, emoji_font, COLORS['text'])

    # Award name
    award_font = get_font(55, bold=True)
    draw_text_centered(draw, award_name, 350, award_font, COLORS['accent'])

    # Detail
    detail_font = get_font(28)
    # Wrap detail text if needed
    if len(award_detail) > 60:
        # Split into two lines
        words = award_detail.split()
        mid = len(words) // 2
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
        draw_text_centered(draw, line1, 440, detail_font, COLORS['text'])
        draw_text_centered(draw, line2, 480, detail_font, COLORS['text'])
    else:
        draw_text_centered(draw, award_detail, 440, detail_font, COLORS['text'])

    return img


def generate_all_cards(
    stats: WrappedStats,
    enrichment: dict[str, Any],
    output_dir: Path,
) -> list[Path]:
    """Generate all PNG cards for sharing.

    Args:
        stats: Wrapped statistics
        enrichment: Enrichment data
        output_dir: Directory to save cards

    Returns:
        List of paths to generated cards
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    # Hero card
    hero = generate_hero_card(stats)
    hero_path = output_dir / "hero-stats.png"
    hero.save(hero_path)
    generated.append(hero_path)

    # Tool fingerprint card
    if enrichment.get('fingerprint'):
        tool_card = generate_tool_fingerprint_card(stats, enrichment['fingerprint'])
        tool_path = output_dir / "tool-fingerprint.png"
        tool_card.save(tool_path)
        generated.append(tool_path)

    # Agent comparison card
    if stats.total_sessions > 0:
        agent_card = generate_agent_comparison_card(stats)
        agent_path = output_dir / "agent-comparison.png"
        agent_card.save(agent_path)
        generated.append(agent_path)

    # Award cards (up to 3)
    awards = enrichment.get('awards', [])
    for i, award in enumerate(awards[:3]):
        award_card = generate_award_card(
            award['name'],
            award['emoji'],
            award['detail'],
            stats.year,
        )
        award_path = output_dir / f"award-{award['id']}.png"
        award_card.save(award_path)
        generated.append(award_path)

    return generated
