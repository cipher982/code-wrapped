# Code Wrapped

Your AI Coding Year in Review - Spotify Wrapped for AI coding agents.

Analyzes your sessions across Claude Code, Codex, Cursor, and Gemini to create a personalized, shareable year-in-review with stats, insights, and beautiful visualizations.

## Quick Start

```bash
# Install
uv sync

# Run for current year (generates HTML report + PNG cards)
uv run code-wrapped run --year 2025

# With LLM-generated narrative
uv run code-wrapped run --year 2025 --narrate

# Skip visual generation (JSON only)
uv run code-wrapped run --year 2025 --no-report
```

## What You Get

**Output files (in `data/output/`):**
- `wrapped-{year}.html` - Beautiful single-page HTML report with interactive charts
- `wrapped-{year}.json` - Full stats (sessions, turns, tokens, tools, repos)
- `wrapped-{year}-share.json` - Privacy-safe subset for sharing
- `cards/` directory with PNG cards:
  - `hero-stats.png` - Big numbers summary
  - `agent-comparison.png` - Usage split across agents
  - `tool-fingerprint.png` - Your coding DNA
  - `award-*.png` - Your earned awards

**What's Analyzed:**
- Sessions, turns, tokens consumed
- Tool usage patterns (Bash, Read, Edit, etc)
- Coding topics and vibes
- Time patterns (peak hours, streaks)
- Repository activity
- Prompt archetypes (architect, debugger, explorer, etc)
- Auto-detected awards (Night Owl, Marathon Coder, etc)

## Supported Agents

- Claude Code
- Codex
- Cursor
- Gemini

## Features

- **Phase 1: Core Stats** - Parse sessions, aggregate metrics
- **Phase 2: Semantic Analysis** - Topic detection, vibes, tool fingerprints, archetypes
- **Phase 3: Narrative Generation** - LLM-powered insights and storytelling
- **Phase 4: Visual Generation** - HTML reports, PNG cards, interactive charts
- **Phase 5: Cross-Agent Analysis** - Coming soon
