# Omni Browser Agent — Implementation Plan

A production-ready, autonomous browser agent system built on Python 3.12 + Playwright
that can execute any browser task and deeply integrate with social media platforms.
It extends the existing Super_Agent ecosystem (OCR_Agent, Browser_Info_Scraper) with
a new peer sub-agent — the **Omni-Browser Agent**.

---

## User Review Required

> [!IMPORTANT]
> **Credentials Needed Before Execution**
> The following API keys / secrets must be provided (or stubbed in `.env`):
> - `NVIDIA_API_KEY` — reused from existing ecosystem (already confirmed present)
> - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — for YouTube OAuth 2.0
> - `INSTAGRAM_USERNAME` / `INSTAGRAM_PASSWORD` — for session-cookie auth
> - `LINKEDIN_USERNAME` / `LINKEDIN_PASSWORD` — for LinkedIn informal API
> - `TWITTER_BEARER_TOKEN` — for Twitter/X v2 API (free tier)
> - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` — optional; used only if NVIDIA model fallback needed
> The system will still boot and run in **demo/stub mode** with fake credentials.

> [!WARNING]
> **Playwright Browser Binary Download (~200 MB)**
> On first `playwright install`, Chromium/Firefox binaries are downloaded. This is a
> one-time setup step and requires internet access.

> [!CAUTION]
> **Instagram & LinkedIn scraping is against their ToS.**
> The system uses authenticated session cookies (not headless scraping of public pages)
> and is designed for personal research use only. Rate-limit guards are built in.

---

## Architecture Overview

```
omni-browser agent/
├── .agent/
│   └── workflows/                  ← Workflow YAML definitions
│       ├── browser_task.md
│       ├── social_media_harvest.md
│       └── debate_synthesize.md
├── core/
│   ├── config.py                   ← Pydantic BaseSettings (YAML + .env)
│   ├── config.yaml                 ← All tunable parameters
│   ├── exceptions.py               ← Custom exception hierarchy
│   └── logger.py                   ← Structured JSON logger (Rich console)
├── models/
│   └── schemas.py                  ← All Pydantic I/O contracts
├── auth/
│   └── manager.py                  ← OAuth2 + cookie session manager
├── browser/
│   ├── engine.py                   ← Playwright async engine (launch/teardown)
│   ├── navigator.py                ← AI-driven page navigation (NVIDIA LLM)
│   └── actions.py                  ← Atomic browser actions (click, fill, scroll)
├── pipeline/
│   ├── task_router.py              ← Intent classifier → dispatches to right handler
│   ├── extractor.py                ← YouTube (transcript-api + yt-dlp), IG, LI, X
│   ├── ai_inference.py             ← NVIDIA vision + ASR inference wrappers
│   └── sanitizer.py               ← Prompt injection scrubber for scraped content
├── engine/
│   ├── debate.py                   ← 3-step Prompt History & Debate Engine
│   └── memory.py                   ← Session history (in-memory + Redis optional)
├── agents/
│   └── crew.py                     ← CrewAI agent + task definitions
├── output/
│   └── formatter.py               ← Markdown / JSON structured output formatter
├── ui/
│   ├── dashboard.html              ← Rich web UI (served via FastAPI static)
│   ├── dashboard.js
│   └── dashboard.css
├── api/
│   └── server.py                  ← FastAPI HTTP server (REST + WebSocket)
├── tests/
│   ├── test_pipeline.py
│   ├── test_debate_engine.py
│   ├── test_browser_engine.py
│   └── conftest.py
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── main.py                         ← CLI entrypoint
```

---

## Proposed Changes

### Phase 1 — Foundation

#### [NEW] `.env.example`
All API keys, OAuth secrets, platform credentials, and feature flags.

#### [NEW] `core/config.py`
`Pydantic BaseSettings` loading from `config.yaml` + `.env`. Singleton freeze pattern
matching the OCR_Agent's proven pattern. Adds `BrowserConfig`, `SocialConfig`,
`DebateConfig`, `RedisConfig` sections.

#### [NEW] `core/config.yaml`
Master YAML with all tunable params: timeouts, model IDs, concurrency limits,
rate-limit windows, platform-specific flags.

#### [NEW] `core/exceptions.py`
Full custom exception hierarchy:
```
OmniBrowserError
├── AuthExpiredError
├── AgentAuthError
├── PlatformRateLimitError
├── CaptchaBlockError
├── BrowserLaunchError
├── NavigationTimeoutError
├── ExtractionError
│   ├── TranscriptUnavailableError
│   ├── MediaDownloadError
│   └── AudioProcessingError
├── DebateResolutionError
└── PromptInjectionDetectedError
```

#### [NEW] `core/logger.py`
Rich console + JSON file logger. Component-aware: every log line includes
`[ComponentName]` prefix. Writes to `logs/omni_browser.log`.

#### [NEW] `models/schemas.py`
Pydantic models:
- `AgentConfig`, `BrowserTask`, `TaskResult`
- `PlatformPost`, `YouTubeVideo`, `InstagramPost`, `LinkedInPost`, `Tweet`
- `ExtractionResult` (extends OCR_Agent's schema for inter-agent compatibility)
- `DebateContext`, `SessionHistory`, `SynthesizedPrompt`
- `APIErrorEnvelope`

---

### Phase 2 — Browser Engine

#### [NEW] `browser/engine.py`
Async Playwright engine. Manages browser lifecycle (launch, context, page pooling).
Supports `chromium`, `firefox`, `webkit`. Headless/headed mode toggled via config.
Injects stealth scripts to avoid bot detection.

#### [NEW] `browser/navigator.py`
AI-driven navigator using NVIDIA LLM. Given a natural language goal, it:
1. Captures a screenshot of the current page
2. Sends it to the NVIDIA Vision model with the goal
3. Parses the LLM's response to determine the next atomic action
4. Executes it via `actions.py`
Loops until goal is achieved or max_steps reached.

#### [NEW] `browser/actions.py`
Atomic browser primitives: `click`, `fill`, `scroll`, `hover`, `wait_for`,
`navigate`, `screenshot`, `extract_text`, `download_file`.

---

### Phase 3 — Auth Manager

#### [NEW] `auth/manager.py`
- **Google/YouTube**: OAuth 2.0 PKCE flow. Token refresh on `401`. Saves tokens to
  encrypted local store.
- **Instagram**: Cookie-based session via `instagrapi`. Catches `LoginRequired`,
  emits `AuthExpiredError`.
- **LinkedIn**: Cookie-based session via `linkedin-api`. Refresh guard.
- **Twitter/X**: Bearer token (read-only) + OAuth 1.0a for write operations.

---

### Phase 4 — Extraction Pipeline

#### [NEW] `pipeline/task_router.py`
Intent classifier: parses user's natural language task and routes to:
- `BrowserTaskHandler` (generic browser automation)
- `YouTubeExtractor`
- `InstagramExtractor`
- `LinkedInExtractor`
- `TwitterExtractor`
- `WebResearchHandler`

#### [NEW] `pipeline/extractor.py`
**YouTube (3-path waterfall)**:
1. `youtube-transcript-api` (instant, no download)
2. `yt-dlp` + `ffmpeg` audio split → Whisper ASR (fallback)
3. `yt-dlp` + OpenCV frame extraction @1fps/5s → Vision model (last resort)

**Instagram**: `instagrapi` → post metadata + caption + media URL
**LinkedIn**: `linkedin-api` → post text + reactions
**Twitter/X**: Twitter API v2 → tweet text + media

**VAD gate**: Before Whisper, check voice activity; music-only reels get
`Audio: Music/Non-vocal` label instead of hallucinated transcript.

#### [NEW] `pipeline/ai_inference.py`
Async wrappers for all NVIDIA model calls:
- `run_vision_analysis(image_path, prompt)` → `VisionResult`
- `run_audio_transcription(audio_path)` → `TranscriptionResult`
- `run_llm_completion(messages)` → `str`

#### [NEW] `pipeline/sanitizer.py`
Sanitizes scraped text before passing to LLM context.
Strips/escapes: `<system>`, `<user>`, `[INST]`, role-injection patterns.
Logs detections as `PromptInjectionDetectedError` (non-fatal, content cleaned).

---

### Phase 5 — Debate Engine & Memory

#### [NEW] `engine/memory.py`
- In-memory `SessionHistory` (LRU-capped at 100 entries)
- Optional Redis persistence (enabled via config)
- Thread-safe via `asyncio.Lock`

#### [NEW] `engine/debate.py`
3-Step Prompt Synthesis:
1. **Intent Analysis**: Extract intent from both Prompt A (historical) and Prompt B (new)
2. **Chain-of-Thought Debate**: LLM internal debate identifying conflicts & overlaps
3. **Synthesis**: Generate new unified prompt; if mutually exclusive, prioritize B,
   alert user about dropped constraint from A

---

### Phase 6 — API Server & UI

#### [NEW] `api/server.py`
FastAPI server:
- `POST /task` — submit browser task
- `GET /tasks/{id}` — poll task status
- `WebSocket /ws/tasks/{id}` — live streaming output
- `GET /history` — session history
- `POST /debate` — submit two prompts for synthesis
- Serves `ui/` as static files

#### [NEW] `ui/dashboard.html` + `dashboard.js` + `dashboard.css`
Premium dark-mode UI:
- Live task submission form
- Real-time output streaming via WebSocket
- Session history panel
- Debate engine interface (side-by-side prompt comparison)
- Platform status indicators (auth state per platform)
- Animated task progress timeline

---

### Phase 7 — Agent Wiring

#### [NEW] `agents/crew.py`
CrewAI Agent + Task definitions. The `OmniBrowserAgent` wraps all tools and is
orchestrated by the `TaskRouter`. Supports delegation to OCR_Agent sub-agent
for file extraction tasks.

#### [NEW] `main.py`
CLI entrypoint supporting:
- `python main.py task "open youtube and find AI news"` — single task
- `python main.py server` — start FastAPI + UI
- `python main.py batch --file tasks.json` — batch execution
- `python main.py debate "prompt A" "prompt B"` — debate two prompts

---

### Phase 8 — Workflows

#### [NEW] `.agent/workflows/browser_task.md`
Step-by-step workflow for executing arbitrary browser automation tasks.

#### [NEW] `.agent/workflows/social_media_harvest.md`
Workflow for platform-specific content harvesting.

#### [NEW] `.agent/workflows/debate_synthesize.md`
Workflow for running the prompt history debate engine.

---

### Phase 9 — Docker

#### [NEW] `Dockerfile`
Multi-stage: `python:3.12-slim` base + Playwright browser install + app layer.

#### [NEW] `docker-compose.yml`
Services: `omni-agent` (main worker) + `redis` (optional session store) +
`nginx` (reverse proxy for UI).

---

### Phase 10 — Tests

#### [NEW] `tests/conftest.py`
Shared fixtures: mocked NVIDIA client, fake browser page, sample social posts.

#### [NEW] `tests/test_pipeline.py`
Tests: `YouTubeExtractor`, `InstagramExtractor`, `TaskRouter`. Offline mocks via
`pytest-asyncio` + `responses`.

#### [NEW] `tests/test_debate_engine.py`
Tests: conflict detection, synthesis, mutual-exclusion handling, LRU eviction.

#### [NEW] `tests/test_browser_engine.py`
Tests: browser launch, navigation loop, action execution, screenshot capture.

---

## Open Questions

> [!IMPORTANT]
> **Q1: Execution Model**
> Should the agent run as:
> (a) A **standalone FastAPI server** with web UI (recommended — full dashboard)
> (b) A **CLI-only tool** (simpler, no web UI needed)
> (c) **Both** (CLI + server mode switchable via command)
> → Default plan: **(c) Both**

> [!IMPORTANT]
> **Q2: LLM Backend for Navigation**
> For AI-driven browser navigation (reading screenshots and deciding actions):
> (a) **NVIDIA NIM** (existing ecosystem, consistent with OCR_Agent)
> (b) **Google Gemini** (multimodal, strong vision)
> (c) **OpenAI GPT-4o** (industry standard)
> → Default plan: **(a) NVIDIA NIM** to stay consistent with existing ecosystem

> [!IMPORTANT]
> **Q3: Playwright vs Selenium**
> (a) **Playwright** (async-first, modern, recommended)
> (b) **Selenium** (legacy, wider support)
> → Default plan: **(a) Playwright**

> [!IMPORTANT]
> **Q4: Social Media Priority**
> Which platforms should be fully implemented vs stubbed?
> → Default plan: **YouTube (full)**, **Instagram (full)**, **LinkedIn (stub)**, **Twitter/X (stub)**
> All four can be full if needed.

---

## Verification Plan

### Automated Tests
```bash
cd "e:\Super_Agent\omni-browser agent"
python -m pytest tests/ -v --asyncio-mode=auto
```

### Manual Verification
1. Start the FastAPI server: `python main.py server`
2. Open browser to `http://localhost:8000`
3. Submit a browser task: `"Search Google for Python async tutorials and return top 5 results"`
4. Verify WebSocket live output streams correctly
5. Test YouTube extraction with a public video URL
6. Test Debate Engine with two contradictory prompts
