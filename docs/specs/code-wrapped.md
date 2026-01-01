# Code Wrapped: Your AI Coding Year in Review

## Executive Summary

A "Spotify Wrapped" style experience for AI-assisted coding. Analyzes your sessions across Claude Code, Codex, Cursor, and Gemini to create a personalized, shareable year-in-review that tells the story of your coding journey through data and insights.

**Target:** End-of-year 2025 retrospective with viral shareability.

---

## MVP Definition (What Ships First)

**The "It Works" MVP:**
```bash
code-wrapped run --year 2025
# Outputs:
#   data/output/wrapped-2025.html    # Single-page report
#   data/output/cards/               # 3-4 PNG share cards
#   data/output/wrapped-2025.json    # Raw stats
```

**MVP Scope:**
1. Parse all 4 agents → unified stats JSON
2. Basic visualizations (heatmap, tool fingerprint, agent comparison)
3. Simple keyword-based topic detection (no ML clustering)
4. LLM-generated narrative (optional, behind `--narrate` flag)
5. Static HTML report + shareable PNG cards
6. Privacy-safe defaults (no code snippets, sanitized paths)

**NOT in MVP:**
- Animated story mode (Phase 2)
- AI-generated art (Phase 2)
- Complex ML clustering (Phase 2)
- Web server/app (Phase 2)

---

## Codex Review Feedback (Incorporated)

**From independent Codex review (Dec 31, 2025):**
- [x] Tighten MVP scope - was "v1 product", now true MVP
- [x] Add canonical Session schema with field mappings
- [x] Specify privacy model with redaction defaults
- [x] Replace HDBSCAN with simpler TF-IDF/KMeans fallback
- [x] Add output architecture (where files go, naming)
- [x] Add time handling (timezone, year selection)
- [x] Add creative ideas: Error of Year, Agent Handoffs, Prompt Archetypes

---

## Decision Log

### Decision: Multi-Agent Architecture
**Context:** Need to support Claude, Codex, Cursor, and Gemini with different data formats
**Choice:** Unified data model with agent-specific parsers (already exists in cipher982)
**Rationale:** Maximizes reuse, enables cross-agent comparisons
**Revisit if:** New agent formats are significantly different

### Decision: ML via Embeddings + LLM Synthesis
**Context:** Want intelligent insights, not just counts
**Choice:** Use embeddings for clustering/similarity, LLM calls for narrative generation
**Rationale:** Embeddings scale cheaply, LLM provides human-readable insights
**Revisit if:** Token costs become prohibitive

### Decision: Web-First with Story Mode
**Context:** Spotify Wrapped's success is mobile-first stories format
**Choice:** Build as web app with "tap-through story" UX pattern
**Rationale:** Easy sharing, works everywhere, enables animations
**Revisit if:** Native apps become priority

---

## Data Sources

### Available Raw Data

| Agent | Location | Format | Key Fields |
|-------|----------|--------|------------|
| Claude Code | `~/.claude/projects/*/` | JSONL | messages, tool_use, tokens, model, timestamp, repo |
| Codex | `~/.codex/sessions/` | JSONL | messages, cwd, timestamp, git info |
| Cursor | `~/Library/.../state.vscdb` | SQLite | composerData, bubbles, mode, timestamp |
| Gemini | `~/.gemini/tmp/*/logs.json` | JSON | messages, sessionId, timestamp |
| GitHub | git repos | git log | commits, branches, timestamps |

### Canonical Session Schema

```python
@dataclass
class Session:
    """Unified session model across all agents."""

    # Identity
    id: str                          # Unique session ID
    agent: Literal["claude", "codex", "cursor", "gemini"]

    # Timing
    started_at: datetime             # UTC timestamp
    ended_at: Optional[datetime]     # Computed from last message
    duration_minutes: float          # Computed

    # Context
    repo: Optional[str]              # Sanitized repo name (not full path)
    branch: Optional[str]

    # Metrics
    turn_count: int                  # Total messages (user + assistant)
    user_message_count: int
    assistant_message_count: int
    token_count: Optional[int]       # If available (Claude has this)

    # Tool Usage (Claude/Codex specific)
    tools_used: Dict[str, int]       # {"Bash": 45, "Edit": 23, ...}

    # Content (for analysis, not storage)
    user_prompts: List[str]          # Redacted/sanitized

    # Enriched (computed later)
    topic: Optional[str]             # Detected topic
    vibe: Optional[str]              # "debugging", "flow", "exploration"

    # Graceful unknowns
    _parse_errors: List[str]         # Track what couldn't be parsed


# Per-agent field mappings
FIELD_MAP = {
    "claude": {
        "id": "sessionId",
        "started_at": "timestamp",  # First message
        "repo": lambda cwd: extract_repo_from_path(cwd),
        "tools_used": lambda msgs: count_tool_uses(msgs),
    },
    "codex": {
        "id": "payload.id",
        "started_at": "payload.timestamp",
        "repo": lambda cwd: extract_repo_from_path(cwd),
    },
    # ... etc
}
```

### Privacy Model

**Default: Safe for sharing**

| Data Type | Treatment | Rationale |
|-----------|-----------|-----------|
| Full paths | Redact to repo name only | `/Users/dave/git/secret-project` → `secret-project` |
| Code snippets | Never include | Could contain secrets/IP |
| Commit messages | Include (opt-in) | Usually safe, but flag available |
| Error messages | Include, redact paths | Useful for "Error of the Year" |
| API keys/secrets | Scan and redact | Pattern matching for common formats |
| User prompts | Include summaries only | Full prompts may leak context |

**Privacy flags:**
```bash
code-wrapped run --year 2025 --privacy=strict   # No repo names, no prompts
code-wrapped run --year 2025 --privacy=normal   # Default: repo names, no code
code-wrapped run --year 2025 --privacy=full     # Everything (local use only)
```

### Enriched Data (computed)

| Field | Description | Method (MVP) | Method (Phase 2) |
|-------|-------------|--------------|------------------|
| `topic` | What you were working on | Keyword matching + TF-IDF | Embeddings → KMeans |
| `vibe` | Session mood | Keyword heuristics | Sentiment classifier |
| `complexity_score` | Task complexity | Turn count + token count | LLM analysis |
| `tool_fingerprint` | Usage patterns | Frequency analysis | Same |
| `prompt_archetype` | Prompt style | Pattern matching | Same |

### Time Handling

```python
# Default: current year in local timezone
year = 2025
timezone = "America/Los_Angeles"  # From system or --tz flag

# Date range for "Year 2025"
start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=tz)
end = datetime(2025, 12, 31, 23, 59, 59, tzinfo=tz)
```

### Output Architecture

```
data/output/
├── wrapped-2025.json              # Full stats (private)
├── wrapped-2025.html              # Single-page report
├── wrapped-2025-share.json        # Privacy-safe subset
└── cards/
    ├── hero-stats.png             # Main numbers card
    ├── tool-fingerprint.png       # Your tool DNA
    ├── agent-comparison.png       # Claude vs Codex vs ...
    └── award-{name}.png           # Per-award cards
```

---

## Feature Spec

### Phase 1: Core Stats & Parsing (Foundation)

**Goal:** Unified data collection from all agents with enriched metrics.

#### 1.1 Data Collection
- [ ] Copy/adapt parsers from cipher982 repo
- [ ] Unified `Session` model with common fields
- [ ] Full-year parsing (not just 7/30 days)
- [ ] Token usage aggregation
- [ ] Tool usage extraction (Bash, Edit, Read, etc.)

#### 1.2 Basic Stats
- [ ] Total sessions per agent
- [ ] Total turns/messages
- [ ] Total tokens consumed
- [ ] Active days (streak tracking)
- [ ] Repository coverage
- [ ] Time-of-day distribution

**Acceptance Criteria:**
- Parse all 4 agents successfully
- JSON output with all basic stats
- Tests with fixture data

---

### Phase 2: Semantic Analysis (ML Layer)

**Goal:** Extract meaning from conversation content.

#### 2.1 Topic Clustering
```python
# Embed all user prompts
embeddings = embed_model.encode(user_messages)

# Cluster into topics
clusters = HDBSCAN(min_cluster_size=5).fit(embeddings)

# LLM-name each cluster
for cluster in clusters:
    name = llm.complete(f"Name this coding topic cluster: {samples}")
```

**Output:** Your Top 5 coding topics with session counts

#### 2.2 Session Sentiment/Vibe Detection
```python
VIBES = {
    "debugging_hell": ["error", "not working", "why", "wtf", "help"],
    "flow_state": ["perfect", "works", "great", "done", "ship it"],
    "exploration": ["what if", "could we", "try", "experiment"],
    "learning": ["how do", "explain", "understand", "what is"]
}
```

**Output:** Your coding vibe breakdown (pie chart)

#### 2.3 "Your Coding DNA" (Tool Usage Fingerprint)
```
Your Fingerprint:
  Bash     ████████████ 42%
  Edit     ████████░░░░ 28%
  Read     █████░░░░░░░ 18%
  Write    ███░░░░░░░░░ 12%

You're a "Terminal Warrior" - command-line first, edit later.
```

**Acceptance Criteria:**
- Topic clusters with LLM-generated names
- Sentiment/vibe breakdown
- Tool fingerprint visualization

---

### Phase 3: Narrative Generation (Storytelling) ✅ COMPLETE

**Status:** Implemented December 31, 2025

**Goal:** Turn stats into compelling human stories.

#### 3.1 LLM-Generated Insights
```python
context = {
    "total_sessions": 847,
    "favorite_topic": "API integrations",
    "longest_session": {"hours": 4.2, "topic": "debugging auth"},
    "night_owl_score": 0.73,
    "top_repo": "zerg",
    "claude_vs_codex_split": "62/38"
}

narrative = llm.complete(f"""
You are writing a "Spotify Wrapped" style summary for a developer.
Make it personal, surprising, and slightly playful.

Stats: {context}

Generate:
1. A headline stat that sounds impressive
2. A "your vibe this year" description
3. A surprising insight
4. A "most epic moment" callout
""")
```

#### 3.2 Superlatives & Awards
Auto-generated awards based on data patterns:

| Award | Criteria | Example |
|-------|----------|---------|
| "Bug Slayer" | Most debugging sessions | "You squashed 47 bugs in October alone" |
| "Night Owl" | Late-night coding | "Your peak hour was 2AM" |
| "Polyglot" | Multiple languages | "You touched 8 languages this year" |
| "AI Whisperer" | High avg turns/session | "Your conversations averaged 340 turns" |
| "Speed Demon" | Fast session completions | "Your fastest fix: 3 minutes" |
| "Deep Diver" | Long sessions | "Your longest session: 4h 23m on auth" |
| "Repo Hopper" | Many repos | "You worked across 23 repositories" |

**NEW from Codex Review - Creative Additions:**

| Feature | Description | Implementation |
|---------|-------------|----------------|
| "Error of the Year" | Most memorable error encountered | Extract from tool_result errors, LLM pick best |
| "Command of the Year" | Most-used or most epic command | Frequency analysis of Bash commands |
| "Agent Handoff Moments" | Detect mid-problem agent switches | Timeline where user switched Claude→Codex |
| "Debugging Arc" | Longest unresolved→breakthrough→resolution | Session chain analysis |
| "Prompt Archetypes" | Categorize your prompts | design/debug/refactor/explain/test/ship labels |
| "Privacy-First Share Mode" | Anonymous Wrapped toggle | `--anonymous` flag strips all identifiers |

#### 3.3 Prompt Archetypes

Categorize prompts into personality types:

```python
PROMPT_ARCHETYPES = {
    "architect": ["design", "structure", "architecture", "refactor", "organize"],
    "debugger": ["fix", "error", "bug", "not working", "broken", "why"],
    "explorer": ["how", "what", "explain", "understand", "learn"],
    "builder": ["add", "create", "implement", "build", "new feature"],
    "shipper": ["deploy", "release", "push", "publish", "ship"],
    "tester": ["test", "verify", "check", "validate", "coverage"],
}

# Output: "You're 45% Debugger, 30% Builder, 15% Architect..."
```

**Acceptance Criteria:**
- ✅ LLM-generated narrative paragraphs
- ✅ At least 5 auto-detected awards (12 award types implemented)
- ✅ Personalized based on actual outliers in data
- ✅ Prompt archetype breakdown included (implemented in Phase 2)

**Implementation Summary:**

**What Was Built:**
- `narrative/story.py`: Compiles `NarrativeContext` from stats, awards, and enrichment
- `narrative/insights.py`: LLM-powered narrative generation via Anthropic API
  - Generates 6 narrative sections: headline, year summary, vibe description, surprising insight, epic moment, personal note
  - Graceful fallback when ANTHROPIC_API_KEY not available
  - Graceful fallback when anthropic package not installed
- CLI integration: `--narrate/-n` flag enables narrative mode
- `print_narrative()` displays formatted LLM insights before stats summary
- Comprehensive test suite: 13 tests with mocked API responses

**LLM Prompt Design:**
- System prompt sets "Spotify Wrapped" tone: playful, personal, celebratory
- Context string includes all key stats and patterns
- Structured output format ensures consistent parsing
- Temperature=0.8 for creative variation

**Graceful Degradation:**
1. No API key → Returns None, prints warning message
2. Import error → Returns None (anthropic not installed)
3. API error → Returns None, fails silently
4. User can run without `--narrate` to see stats only

**Not Yet Implemented (Future Phases):**
- "Error of the Year" feature (requires error collection from tool_results)
- "Command of the Year" (requires Bash command extraction)
- "Agent Handoff Moments" (requires temporal analysis)
- Award flavor text enhancement via LLM (optional function exists but not integrated)

---

### Phase 4: Visual Generation (The Wow Factor)

**Goal:** Create shareable, beautiful visuals.

#### 4.1 Static Visualizations
- **Hero Card:** Summary stats in branded design
- **Heatmap:** Your coding year calendar (GitHub-style but richer)
- **Radar Chart:** Skills/topics pentagon
- **Timeline:** Your coding journey milestones
- **Bar Race:** Monthly topic evolution (animated)

#### 4.2 AI-Generated Art
```python
# Generate personalized "album art" for your coding year
prompt = f"""
Abstract digital art representing a developer's year:
- Primary theme: {top_topic}  # e.g., "AI/ML development"
- Mood: {dominant_vibe}  # e.g., "focused and experimental"
- Colors: {agent_colors}  # Claude blue, Codex green
- Style: Geometric, modern, tech-inspired
"""

image = image_model.generate(prompt)
```

**Output:** Unique, shareable "album cover" for your coding year

#### 4.3 Animated Story Mode
Tap-through story format (like Instagram/Spotify):

```
[Slide 1: The Opening]
"In 2024, you weren't just coding.
You were co-creating with AI."

[Slide 2: The Numbers]
*animated counter*
"847 sessions. 287,000 turns. One epic year."

[Slide 3: Your Top Topic]
*fade in topic cloud*
"You couldn't stop thinking about: API INTEGRATIONS"

[Slide 4: Your Vibe]
*pie chart animation*
"You spent 43% of your time in flow state. Nice."

[Slide 5: The Award]
*award reveal animation*
"You earned: THE NIGHT OWL"
"Peak productivity: 2AM"

[Slide 6: Your AI Partner]
*agent comparison*
"Claude was your go-to (62%), but Codex was your debugging buddy."

[Slide 7: The Art]
*AI-generated image reveal*
"Your coding year, visualized."

[Slide 8: Share]
"Share your Code Wrapped"
[Twitter] [LinkedIn] [Download]
```

**Acceptance Criteria:**
- Story mode with 6-8 slides
- Animations/transitions
- Shareable images for each slide
- AI-generated hero art

---

### Phase 5: Cross-Agent Analysis (Unique Angle)

**Goal:** Compare how you use different AI agents.

#### 5.1 Agent Personality Profiles
```
CLAUDE: Your "Architect"
- Used for: System design, refactoring, documentation
- Avg session length: 45 min
- Tool preference: Edit (38%)

CODEX: Your "Debugger"
- Used for: Bug fixes, quick scripts
- Avg session length: 12 min
- Tool preference: Bash (52%)

CURSOR: Your "Explorer"
- Used for: Prototyping, learning new APIs
- Avg session length: 20 min
- Mode: Agent (67%)
```

#### 5.2 Agent Switching Patterns
When do you switch agents? Time of day? Project type? Stuck patterns?

**Acceptance Criteria:**
- Per-agent stats breakdown
- "Personality" description for each agent
- Recommendations: "Use Claude more for X"

---

## Technical Architecture

```
code-wrapped/
├── src/
│   ├── parsers/          # Agent-specific parsers
│   │   ├── claude.py
│   │   ├── codex.py
│   │   ├── cursor.py
│   │   └── gemini.py
│   ├── enrichment/       # ML enrichment
│   │   ├── embeddings.py
│   │   ├── clustering.py
│   │   ├── sentiment.py
│   │   └── fingerprint.py
│   ├── narrative/        # LLM generation
│   │   ├── insights.py
│   │   ├── awards.py
│   │   └── story.py
│   ├── viz/              # Visualization
│   │   ├── charts.py
│   │   ├── hero.py
│   │   └── story_mode.py
│   └── web/              # Web app
│       ├── app.py        # FastAPI/Flask
│       └── templates/
├── data/
│   ├── raw/              # Parsed session data
│   ├── enriched/         # With ML annotations
│   └── output/           # Generated assets
├── docs/
│   └── specs/
└── tests/
```

### Dependencies

```toml
[dependencies]
# Parsing
pydantic = "^2.0"

# ML/Embeddings
sentence-transformers = "^2.2"
hdbscan = "^0.8"
numpy = "^1.24"

# LLM
anthropic = "^0.30"  # or openai

# Visualization
matplotlib = "^3.7"
plotly = "^5.15"
pillow = "^10.0"

# Image Generation (optional)
replicate = "^0.15"  # or stability-ai

# Web
fastapi = "^0.100"
jinja2 = "^3.1"
```

---

## Implementation Phases

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| 1 | Data Collection | Unified parsed JSON from all agents |
| 2 | ML Enrichment | Topic clusters, vibes, fingerprints |
| 3 | Narrative | LLM-generated stories and awards |
| 4 | Visualization | Static charts + story mode |
| 5 | Cross-Agent | Agent comparison insights |
| 6 | Polish | Web app, sharing, animations |

---

## Success Metrics

1. **Virality:** Shareable on social media
2. **Personalization:** No two wraps look the same
3. **Wow Factor:** At least one "how did they know that?" moment
4. **Accuracy:** Stats match reality
5. **Speed:** Generate in < 60 seconds

---

## Open Questions

1. **Privacy:** How to handle sensitive code/messages in prompts?
   - Decision: Strip code content, use only metadata + summaries

2. **Image generation cost:** Replicate/DALL-E costs per generation?
   - Decision: Make optional, use pre-generated templates as fallback

3. **Local vs. cloud:** Run embedding locally or API?
   - Decision: Local sentence-transformers for privacy

---

## Inspirations

- Spotify Wrapped (story mode, personalization, shareability)
- GitHub Skyline (3D visualization of contributions)
- Raycast Year in Review (developer-focused stats)
- WakaTime annual reports (time tracking insights)
- Strava Year in Sport (achievement emphasis)
