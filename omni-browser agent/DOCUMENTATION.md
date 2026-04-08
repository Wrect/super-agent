# 📖 Project Anti-Gravity — Complete Documentation

> **Version:** 1.0 · **Last Updated:** April 8, 2026  
> **One-Line Summary:** An autonomous robot that watches Instagram videos and extracts the AI prompts hidden inside them.

---

## 📑 Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [The Big Picture — How It Works](#2-the-big-picture)
3. [Folder & File Map](#3-folder--file-map)
4. [Setup Guide](#4-setup-guide)
5. [Environment Variables](#5-environment-variables)
6. [Core Modules](#6-core-modules)
7. [Configuration Files](#7-configuration-files)
8. [Test & Simulation Scripts](#8-test--simulation-scripts)
9. [Data Files](#9-data-files)
10. [Directory Purposes](#10-directory-purposes)
11. [Operational Modes](#11-operational-modes)
12. [Data Flow Diagram](#12-data-flow-diagram)
13. [Command-Line Usage](#13-command-line-usage)
14. [Troubleshooting](#14-troubleshooting)
15. [Glossary](#15-glossary)

---

## 1. What Is This Project?

Imagine you see a cool AI-generated image on Instagram. You think, *"What prompt did they use?"* But the creator only shows the result, not the prompt.

**Project Anti-Gravity** is a robot that:

1. **Opens Instagram** in a real Chrome browser (like a human would).
2. **Finds videos** in your saved posts, playlists, or the explore feed.
3. **Downloads** those videos to your computer.
4. **Watches** each video frame-by-frame using OCR (reads text from images).
5. **Picks out** frames that contain a lot of text (prompts usually have lots of text on screen).
6. **Sends** those frames to an AI model that reads and extracts the exact prompt.
7. **Cleans** the result by removing personal information (names, phone numbers, emails).
8. **Saves** the extracted prompt into a database (MongoDB cloud or local JSON backup).
9. **Shows** everything in a pretty web dashboard.

Think of it as a **"Prompt Sniper"** — it captures AI prompts from Instagram videos automatically.

---

## 2. The Big Picture

```
USER COMMAND (e.g., "Snipe prompts from 3 reels in travel playlist")
         │
         ▼
  NLP COMMANDER (nlp_commander.py) → Translates English to JSON params
         │
         ▼
  PIPELINE CONDUCTOR (old_main.py) → Orchestrates the 7-step pipeline
         │
    ┌────┼────────────────┐
    ▼    ▼                ▼
 STEP 1  STEP 2        STEP 3
 SCRAPER DOWNLOADER     OCR FILTER
 Finds   Gets .mp4      Finds text
 URLs    files           frames
         │                │
         └────────┬───────┘
                  ▼
           STEP 4: VISION AI (vision_agent.py + crew.py)
           Reads the prompt from frames
                  │
                  ▼
           STEP 5: PRIVACY GUARD (privacy_guard.py)
           Removes personal info
                  │
                  ▼
           STEP 6-7: DATABASE + CLEANUP (database.py)
           Saves results, deletes temp files
                  │
                  ▼
           DASHBOARD (dashboard.py) — Shows results in a web page
```

---

## 3. Folder & File Map

```
e:\browsertool\
│
├── 📁 .agents/               # Agent skill files (AI orchestration)
├── 📁 .venv/                 # Python virtual environment
├── 📁 archives/              # Permanently saved media from download-only mode
├── 📁 config/                # YAML config for CrewAI agent system
│   ├── agents.yaml           # WHO the AI agent is (role, goal, backstory)
│   └── tasks.yaml            # WHAT the AI agent should do
├── 📁 library/               # Reserved for future use (empty)
├── 📁 output/                # Pipeline outputs organized by timestamp
│   └── YYYY-MM-DD_HH-MM/    # Each run gets its own timestamped folder
│       ├── video/            # Downloaded .mp4 files
│       └── prompt/           # Extracted prompt JSON files
├── 📁 temp_media/            # Temporary download staging (auto-cleaned)
├── 📁 testing_downloads/     # Reserved for download tests (empty)
│
├── .env                      # YOUR secret keys (never share this!)
├── .env.example              # Template showing what keys you need
├── requirements.txt          # Python package dependencies
│
├── old_main.py               # ⭐ PRIMARY ORCHESTRATOR — full 7-step pipeline
├── main.py                   # Alternative: NVIDIA direct video upload pipeline
├── scraper.py                # Browser automation — IG login + URL collection
├── media_engine.py           # Downloads videos, extracts frames, runs OCR
├── vision_agent.py           # Sends frames to AI model, reads prompts
├── privacy_guard.py          # PII detection & redaction (Microsoft Presidio)
├── database.py               # MongoDB Atlas + local JSON offline storage
├── crew.py                   # CrewAI agent wrapper for prompt extraction
├── nlp_commander.py          # Natural language → pipeline parameters translator
├── dashboard.py              # Streamlit web dashboard
├── discover_nav.py           # Utility: discovers saved collection names
│
├── FINAL_SIMULATION.py       # End-to-end simulation test runner
├── PROMPT_SNIPE_RESULT.py    # Standalone proof: snipe prompt from a video
├── test_api.py               # Single-video pipeline test
├── test_nav.py               # Browser navigation test
├── test_nvidia_api.py        # NVIDIA NVCF upload & inference test
├── test_ocr.py               # OCR frame extraction test
│
├── ig_session.json           # Saved Instagram cookies (auto-generated)
├── ig_cookies_netscape.txt   # Netscape cookies for yt-dlp (auto-generated)
├── offline_data.json         # Local fallback database
└── PROJECT_ANTI_GRAVITY_MASTER_DOCUMENT.md
```

---

## 4. Setup Guide

**Step 1 — Install Python 3.10+** from python.org.

**Step 2 — Create Virtual Environment:**
```powershell
cd e:\browsertool
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Step 3 — Install Dependencies:**
```powershell
pip install playwright yt-dlp opencv-python easyocr numpy openai python-dotenv pymongo presidio-analyzer presidio-anonymizer streamlit pandas crewai pyyaml requests
pip install -r requirements.txt
playwright install chromium
```

**Step 4 — Configure `.env`:** Copy `.env.example` to `.env` and fill in your keys.

**Step 5 — Login to Instagram:** `python scraper.py login` → Log in manually → Press ENTER.

**Step 6 — Run:** `python old_main.py USERNAME --max 5 --extract-prompts`

**Step 7 — Dashboard:** `streamlit run dashboard.py`

---

## 5. Environment Variables

| Variable | Purpose | Default | Example |
|---|---|---|---|
| `MONGO_URI` | MongoDB Atlas connection | *(none)* | `mongodb+srv://user:pass@cluster.mongodb.net/db` |
| `VISION_BASE_URL` | AI model server URL | `http://localhost:11434/v1` | `https://integrate.api.nvidia.com/v1` |
| `VISION_API_KEY` | API key for AI server | `ollama` | `nvapi-abc123...` |
| `VISION_MODEL` | Which AI model to use | `llava` | `google/gemma-4-31b-it` |

Works with **Ollama** (free/local), **NVIDIA NIM** (cloud), or **OpenAI** (cloud).

---

## 6. Core Modules

### 6.1 `scraper.py` — The Robot Browser

Opens Chrome, logs into Instagram, navigates to saved posts/playlists, scrolls, and collects video URLs.

| Function | Purpose |
|---|---|
| `save_login_session()` | Opens Chrome for manual login, saves cookies to `ig_session.json` |
| `get_instagram_links()` | Loads cookies, navigates, scrolls, collects video/reel URLs |

**Smart Features:**
- **Fuzzy Matching:** Typing `"prompts"` matches a folder called `"prompt"` using `difflib.get_close_matches()`.
- **Human Delays:** Random 2.1–4.7s delays between scrolls to avoid bot detection.
- **Deduplication:** Skips URLs already in the database.
- **Priority:** Returns `/reel/` URLs before `/p/` URLs.

---

### 6.2 `media_engine.py` — The Video Workshop

Downloads videos and extracts text-heavy frames.

| Function | Purpose |
|---|---|
| `download_video()` | Downloads video via yt-dlp with cookie auth + "Unstoppable" fallback |
| `extract_frames()` | Samples frames every 2s, runs EasyOCR, keeps frames with 8+ words |
| `cleanup_temp_files()` | Deletes temp directory contents |
| `_convert_to_netscape_cookies()` | Translates Playwright cookies to Netscape format for yt-dlp |

**"Unstoppable" Downloader:** Phase 1 tries best quality with cookies. If it fails, Phase 2 tries lower quality. If cookies caused the error, retries without them.

**OCR Filter:** Frames with 8+ detected words are kept as base64 JPEG strings in memory (zero disk clutter).

---

### 6.3 `vision_agent.py` — The AI Eyes

Sends frames to an AI model to read prompts from images.

| Function | Purpose |
|---|---|
| `_analyze_single_frame()` | Sends ONE frame to AI, asks to extract the prompt |
| `analyze_video_content()` | Analyzes ALL frames one-by-one, then merges into final answer |

**Phase 1:** Each frame analyzed individually → **Phase 2:** AI merges all results into one clean prompt.

---

### 6.4 `privacy_guard.py` — The Bodyguard

Scans extracted text for PII and replaces with `<REDACTED>`.

**Catches:** `PHONE_NUMBER`, `EMAIL_ADDRESS`, `PERSON`, `LOCATION`

| Function | Purpose |
|---|---|
| `scrub_pii()` | Deep-copies entire dict, scrubs ALL string values recursively |
| `_scrub_text()` | Runs Presidio analyzer + anonymizer on a single string |
| `_scrub_value()` | Recursively walks dicts/lists/strings to scrub everything |

---

### 6.5 `database.py` — The Memory Bank

Stores data in MongoDB Atlas with automatic local JSON fallback.

| Function | Purpose |
|---|---|
| `insert_analyzed_data()` | Inserts doc into MongoDB; falls back to `offline_data.json` |
| `get_all_insights()` | Retrieves ALL stored documents |
| `get_processed_urls_set()` | Returns set of all processed URLs (for deduplication) |

**Hybrid System:** Tries MongoDB first → if connection fails → saves locally with `sync_status: "offline"`.

**Database:** `anti_gravity` → Collection: `ig_insights` → TLS, 5s timeout, retry writes.

---

### 6.6 `old_main.py` — The Conductor (⭐ Primary Entry Point)

Orchestrates the entire 7-step pipeline:

| Step | Action | Module |
|---|---|---|
| 1 | Scrape URLs from Instagram | `scraper.py` |
| 2 | Download each video | `media_engine.py` |
| 3 | Extract text-heavy frames via OCR | `media_engine.py` |
| 4 | Analyze with CrewAI + Vision AI | `crew.py` + `vision_agent.py` |
| 5 | Save extracted prompt JSON | Built-in |
| 6 | Clean up temp files | `media_engine.py` |
| 7 | Store in database | `database.py` |

**CLI Arguments:** `username`, `--max`, `--urls`, `--target`, `--playlist`, `--explore`, `--download-only`, `--extract-prompts`, `--save-media-dir`

---

### 6.7 `main.py` — NVIDIA Video Pipeline (Alternative)

Uploads entire videos to NVIDIA's cloud (NVCF) instead of local frame extraction. Uses `google/gemma-4-31b-it` model.

| Function | Purpose |
|---|---|
| `upload_video_to_nvcf()` | Uploads video to NVIDIA S3, returns Asset ID |
| `extract_prompts_via_nvidia_api()` | Sends Asset ID to vision model for extraction |
| `process_video_pipeline()` | Orchestrates upload → inference → save JSON |

---

### 6.8 `nlp_commander.py` — The English Translator

Type commands in plain English: `"Download 15 videos from saved folder"` → `{"max_videos": 15, "download_only": true}`

Sends your sentence to an LLM → parses JSON → calls `run_pipeline()`.

---

### 6.9 `crew.py` — The AI Team

CrewAI wrapper for autonomous prompt extraction.

- `AntiGravityCrew` class → creates agents/tasks from YAML configs
- `analyze_video_tool` → `@tool` that calls `extract_frames()` + `analyze_video_content()`
- `kickoff(inputs)` → runs the crew sequentially

---

### 6.10 `dashboard.py` — The Control Panel

Streamlit web dashboard: `streamlit run dashboard.py`

Shows metrics (Videos Processed, Prompts Sniped), prompt cards with source URLs, and system status sidebar. Reads from both MongoDB and `offline_data.json`.

---

### 6.11 `discover_nav.py` — The Scout

Lists ALL saved collection names from Instagram. Run `python discover_nav.py` to debug fuzzy matching issues.

---

## 7. Configuration Files

**`config/agents.yaml`** — Defines the CrewAI agent role:
```yaml
prompt_extractor:
  role: "Principal Video Prompt Extraction Specialist"
  goal: "Extract generation prompts accurately from video frames."
  backstory: "You are an elite parser... You never hallucinate prompts."
```

**`config/tasks.yaml`** — Defines the task:
```yaml
extract_prompt_task:
  description: "Analyze the video at {video_path}. Use Analyze Video Tool."
  expected_output: 'JSON with `extracted_prompt` key.'
```

---

## 8. Test & Simulation Scripts

| File | Tests |
|---|---|
| `test_api.py` | Full single-video pipeline (download → frames → vision → PII → cleanup) |
| `test_nav.py` | Browser navigation (load cookies, go to saved page, scroll, collect links) |
| `test_nvidia_api.py` | NVIDIA NVCF upload + Gemma inference |
| `test_ocr.py` | OCR frame extraction only |
| `FINAL_SIMULATION.py` | TWO full simulations (fuzzy OCR + archive) with mission report |
| `PROMPT_SNIPE_RESULT.py` | Standalone: snipe prompt from already-downloaded video |

---

## 9. Data Files

| File | Format | Contains |
|---|---|---|
| `ig_session.json` | JSON dict | Browser cookies + localStorage from IG login |
| `ig_cookies_netscape.txt` | Netscape text | Auto-translated cookies for yt-dlp |
| `offline_data.json` | JSON array | Local backup when MongoDB is unavailable |

---

## 10. Directory Purposes

| Directory | Purpose | Auto-cleaned? |
|---|---|---|
| `output/` | Pipeline outputs by timestamp | No |
| `archives/` | Permanent videos from download-only mode | No |
| `temp_media/` | Temporary download staging | Yes |
| `config/` | YAML configs for CrewAI | No |

---

## 11. Operational Modes

| Mode | Command | What Happens |
|---|---|---|
| **Standard** | `--extract-prompts` | Scrape → Download → OCR → Vision AI → Save |
| **Download Only** | `--download-only` | Download only, $0 AI cost |
| **Playlist** | `--playlist "travel"` | Auto-click into named collection (fuzzy match) |
| **Explore** | `--explore` | Wander public Reels feed |
| **Direct URLs** | `--urls URL1 URL2` | Skip scraping, process specific URLs |

---

## 12. Data Flow Diagram

```
Instagram → scraper.py → List of URLs
                            │
                            ▼
                    media_engine.py/download_video() → .mp4 on disk
                            │
                            ▼
                    media_engine.py/extract_frames() → List[base64] in RAM
                    (EasyOCR filters for 8+ word frames)
                            │
                            ▼
                    crew.py → vision_agent.py → {"extracted_prompt": "..."}
                            │
                            ▼
                    privacy_guard.py/scrub_pii() → Clean JSON
                            │
                     ┌──────┴──────┐
                     ▼             ▼
              MongoDB Atlas   offline_data.json
                     │             │
                     └──────┬──────┘
                            ▼
                    dashboard.py (reads both, deduplicates, displays)
```

---

## 13. Command-Line Usage

```powershell
# Login
python scraper.py login

# Standard pipeline
python old_main.py USERNAME --max 5 --extract-prompts

# Download only
python old_main.py USERNAME --max 20 --download-only

# Playlist mode
python old_main.py USERNAME --playlist "prompts" --max 3 --extract-prompts

# Explore mode
python old_main.py --explore --max 10 --download-only

# Direct URLs
python old_main.py --urls "https://instagram.com/reel/ABC"

# Natural language
python nlp_commander.py "Snipe prompts from 3 reels in travel playlist"

# Dashboard
streamlit run dashboard.py

# Discovery tool
python discover_nav.py
```

---

## 14. Troubleshooting

| Problem | Solution |
|---|---|
| `FileNotFoundError: ig_session.json` | Run `python scraper.py login` |
| No video URLs found | Re-login; IG may have changed layout |
| MongoDB connection failed | Check `.env`; system uses JSON fallback |
| `Cookies file must be Netscape formatted` | Auto-handled by Unstoppable fallback |
| No dense text frames found | Video doesn't show text prompts |
| NVIDIA API 404 | Verify `VISION_MODEL` and `VISION_API_KEY` |
| Fuzzy match: no playlist found | Run `python discover_nav.py` to see names |

---

## 15. Glossary

| Term | Meaning |
|---|---|
| **OCR** | Reads text from pictures |
| **PII** | Personal info (names, phones, emails) |
| **Presidio** | Microsoft tool that finds/removes PII |
| **Playwright** | Controls Chrome with Python |
| **yt-dlp** | Downloads videos from websites |
| **EasyOCR** | Python library that reads text from images |
| **OpenCV (cv2)** | Image/video processing library |
| **CrewAI** | Framework for AI agent teams |
| **Base64** | Represents binary data as text |
| **MongoDB Atlas** | Cloud database service |
| **NVCF** | NVIDIA Cloud Functions |
| **Fuzzy Matching** | Approximate text matching |
| **Pipeline** | Series of data processing steps |
| **Streamlit** | Python web dashboard framework |
| **LLM** | Large Language Model (AI) |

---

> **🎯 End of Documentation.** Covers every file, function, mode, and concept in Project Anti-Gravity.
