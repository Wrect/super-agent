"""config.py — Centralised configuration for Project Omni-Extract.

Loads all settings from ``config.yaml`` and exposes them as frozen dataclass
singletons for backward compatibility.  API keys always come from ``.env``.

Every model name, API URL, timeout, and tunable parameter now lives in
``config.yaml``.  Change once there, propagate everywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env on import so every module gets env vars automatically
load_dotenv()

# ---------------------------------------------------------------------------
# YAML Loader
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_yaml() -> dict[str, Any]:
    """Read and parse the master YAML configuration file.

    Returns:
        Parsed dict tree.  Falls back to an empty dict if the file is
        missing (every dataclass has safe defaults).
    """
    if _CONFIG_PATH.is_file():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


_CFG: dict[str, Any] = _load_yaml()


def _section(key: str) -> dict[str, Any]:
    """Return a config section, defaulting to an empty dict."""
    return _CFG.get(key, {})


# =========================================================================
# API Configuration
# =========================================================================

@dataclass(frozen=True)
class APIConfig:
    """NVIDIA API connection settings."""

    base_url: str = field(
        default_factory=lambda: _section("api").get(
            "base_url", "https://integrate.api.nvidia.com/v1"
        )
    )
    api_key: str = field(
        default_factory=lambda: os.environ.get("NVIDIA_API_KEY", "")
    )

    def validate(self) -> bool:
        """Return True if the API key is present."""
        return bool(self.api_key)


# =========================================================================
# Model Registry
# =========================================================================

@dataclass(frozen=True)
class Models:
    """All NVIDIA model identifiers used across the pipeline."""

    agent_llm: str = field(
        default_factory=lambda: _section("models").get(
            "agent_llm", "nvidia_nim/meta/llama-3.1-70b-instruct"
        )
    )
    vision: str = field(
        default_factory=lambda: _section("models").get(
            "vision", "qwen/qwen3.5-397b-a17b"
        )
    )
    audio_asr: str = field(
        default_factory=lambda: _section("models").get(
            "audio_asr", "nvidia/parakeet-ctc-1.1b-asr"
        )
    )
    video: str = field(
        default_factory=lambda: _section("models").get(
            "video", "qwen/qwen3.5-397b-a17b"
        )
    )


# =========================================================================
# LLM Hyper-parameters
# =========================================================================

@dataclass(frozen=True)
class LLMParams:
    """Tunable parameters for the agent's brain LLM."""

    temperature: float = field(
        default_factory=lambda: _section("llm_params").get("temperature", 0.1)
    )
    max_tokens: int = field(
        default_factory=lambda: _section("llm_params").get("max_tokens", 4096)
    )


# =========================================================================
# Vision Tool Settings
# =========================================================================

_DEFAULT_OCR_PROMPT = (
    "Extract ALL text visible in this image exactly as written. "
    "Include every heading, paragraph, table, caption, watermark, "
    "and any other on-screen text. Preserve the original layout "
    "as closely as possible. Do NOT summarise or paraphrase."
)

_DEFAULT_UNDERSTANDING_PROMPT = (
    "Analyze this image in comprehensive detail. Provide: "
    "1. Scene Description  2. Objects & Elements  3. Text Content  "
    "4. Colors & Style  5. Layout & Composition  6. Context & Purpose. "
    "Be thorough and precise. Do NOT make up details that are not visible."
)


@dataclass(frozen=True)
class VisionToolConfig:
    """Settings for the Vision OCR tool."""

    max_tokens: int = field(
        default_factory=lambda: _section("vision_tool").get("max_tokens", 4096)
    )
    temperature: float = field(
        default_factory=lambda: _section("vision_tool").get("temperature", 0.1)
    )
    timeout_seconds: int = field(
        default_factory=lambda: _section("vision_tool").get("timeout_seconds", 120)
    )
    prompt: str = field(
        default_factory=lambda: _section("vision_tool").get(
            "ocr_prompt", _DEFAULT_OCR_PROMPT
        )
    )
    understanding_prompt: str = field(
        default_factory=lambda: _section("vision_tool").get(
            "understanding_prompt", _DEFAULT_UNDERSTANDING_PROMPT
        )
    )


# =========================================================================
# Audio Tool Settings
# =========================================================================

@dataclass(frozen=True)
class AudioToolConfig:
    """Settings for the Audio Transcription tool."""

    language: str = field(
        default_factory=lambda: _section("audio_tool").get("language", "en")
    )
    timeout_seconds: int = field(
        default_factory=lambda: _section("audio_tool").get("timeout_seconds", 180)
    )


# =========================================================================
# Video Tool Settings
# =========================================================================

@dataclass(frozen=True)
class VideoToolConfig:
    """Settings for the Video Extraction tool."""

    max_frames: int = field(
        default_factory=lambda: _section("video_tool").get("max_frames", 10)
    )
    frame_interval_seconds: float = field(
        default_factory=lambda: _section("video_tool").get(
            "frame_interval_seconds", 5.0
        )
    )
    per_frame_max_tokens: int = field(
        default_factory=lambda: _section("video_tool").get(
            "per_frame_max_tokens", 2048
        )
    )
    per_frame_temperature: float = field(
        default_factory=lambda: _section("video_tool").get(
            "per_frame_temperature", 0.1
        )
    )
    per_frame_timeout: int = field(
        default_factory=lambda: _section("video_tool").get("per_frame_timeout", 120)
    )
    frame_prompt: str = field(
        default_factory=lambda: _section("video_tool").get(
            "frame_prompt",
            "This is a frame extracted from a video. "
            "Extract ALL on-screen text exactly as written. "
            "Also briefly describe the key visual elements "
            "and any actions happening in this frame.",
        )
    )


# =========================================================================
# Agent / Crew Settings
# =========================================================================

@dataclass(frozen=True)
class AgentConfig:
    """CrewAI agent behavioural settings."""

    role: str = field(
        default_factory=lambda: _section("agent").get(
            "role", "Omni-Modal Data Extraction Node"
        )
    )
    goal: str = field(
        default_factory=lambda: _section("agent").get(
            "goal",
            "Autonomously select the correct NVIDIA tool based on file "
            "extension, extract the data, and format it exactly to the "
            "required Pydantic schema. Never hallucinate content — only "
            "return what the tool actually extracted.",
        )
    )
    backstory: str = field(
        default_factory=lambda: _section("agent").get(
            "backstory",
            "You are a specialised data-extraction node inside a larger "
            "AI orchestration pipeline.",
        )
    )
    verbose: bool = field(
        default_factory=lambda: _section("agent").get("verbose", True)
    )
    allow_delegation: bool = field(
        default_factory=lambda: _section("agent").get("allow_delegation", False)
    )
    max_iter: int = field(
        default_factory=lambda: _section("agent").get("max_iter", 5)
    )
    default_confidence: float = field(
        default_factory=lambda: _section("agent").get("default_confidence", 0.85)
    )


# =========================================================================
# Output Settings
# =========================================================================

@dataclass(frozen=True)
class OutputConfig:
    """Settings for the dedicated output directory."""

    base_dir: str = field(
        default_factory=lambda: _section("output").get("base_dir", "./outputs")
    )
    save_json: bool = field(
        default_factory=lambda: _section("output").get("save_json", True)
    )
    save_text: bool = field(
        default_factory=lambda: _section("output").get("save_text", True)
    )
    organize_by_type: bool = field(
        default_factory=lambda: _section("output").get("organize_by_type", True)
    )
    timestamp_files: bool = field(
        default_factory=lambda: _section("output").get("timestamp_files", True)
    )


# =========================================================================
# Batch Processing Settings
# =========================================================================

@dataclass(frozen=True)
class BatchConfig:
    """Settings for folder-level batch processing."""

    max_workers: int = field(
        default_factory=lambda: _section("batch").get("max_workers", 4)
    )
    recursive: bool = field(
        default_factory=lambda: _section("batch").get("recursive", False)
    )
    skip_unsupported: bool = field(
        default_factory=lambda: _section("batch").get("skip_unsupported", True)
    )


# =========================================================================
# Security Settings
# =========================================================================

@dataclass(frozen=True)
class SecurityConfig:
    """Read-only enforcement settings."""

    read_only: bool = field(
        default_factory=lambda: _section("security").get("read_only", True)
    )
    allowed_operations: list[str] = field(
        default_factory=lambda: _section("security").get(
            "allowed_operations", ["read", "list", "stat", "analyze"]
        )
    )
    blocked_operations: list[str] = field(
        default_factory=lambda: _section("security").get(
            "blocked_operations",
            ["write", "delete", "rename", "move", "chmod", "copy_to_source"],
        )
    )


# =========================================================================
# File Extension → Media Type Mapping (from YAML)
# =========================================================================

def _build_extension_map() -> dict[str, str]:
    """Build the extension → category mapping from the YAML config.

    Falls back to hardcoded defaults if the YAML section is missing.
    """
    ft = _section("file_types")
    if not ft:
        # Legacy fallback
        return {
            ".png": "image", ".jpg": "image", ".jpeg": "image",
            ".gif": "image", ".bmp": "image", ".tiff": "image",
            ".tif": "image", ".webp": "image",
            ".pdf": "document",
            ".mp3": "audio", ".wav": "audio", ".flac": "audio",
            ".ogg": "audio", ".m4a": "audio", ".aac": "audio",
            ".mp4": "video", ".mov": "video", ".avi": "video",
            ".mkv": "video", ".webm": "video",
        }

    ext_map: dict[str, str] = {}
    for category, extensions in ft.items():
        if isinstance(extensions, list):
            for ext in extensions:
                ext_map[ext] = category
    return ext_map


EXTENSION_MAP: dict[str, str] = _build_extension_map()


# =========================================================================
# Singleton instances — import these directly
# =========================================================================

API = APIConfig()
MODELS = Models()
LLM_PARAMS = LLMParams()
VISION_CFG = VisionToolConfig()
AUDIO_CFG = AudioToolConfig()
VIDEO_CFG = VideoToolConfig()
AGENT_CFG = AgentConfig()
OUTPUT_CFG = OutputConfig()
BATCH_CFG = BatchConfig()
SECURITY_CFG = SecurityConfig()
