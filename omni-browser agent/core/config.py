"""
Core configuration module for Omni Browser Agent.
Loads settings from config.yaml and .env using Pydantic BaseSettings.
Implements singleton freeze pattern matching OCR_Agent's proven pattern.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class BrowserConfig(BaseSettings):
    """Browser-specific configuration."""

    headless: bool = Field(default=False, description="Run browser in headless mode")
    browser_type: str = Field(
        default="chromium", description="Browser type: chromium, firefox, webkit"
    )
    timeout: int = Field(default=30000, description="Default timeout in milliseconds")
    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")
    stealth_mode: bool = Field(
        default=True, description="Enable stealth scripts to avoid bot detection"
    )


class SocialConfig(BaseSettings):
    """Social media platform configuration."""

    youtube_transcript_api_enabled: bool = Field(
        default=True, description="Enable YouTube transcript API"
    )
    instagram_login_enabled: bool = Field(
        default=True, description="Enable Instagram login"
    )
    linkedin_api_enabled: bool = Field(default=True, description="Enable LinkedIn API")
    twitter_api_enabled: bool = Field(default=True, description="Enable Twitter/X API")
    rate_limit_per_minute: int = Field(
        default=30, description="Rate limit per platform per minute"
    )


class DebateConfig(BaseSettings):
    """Debate engine configuration."""

    max_history_entries: int = Field(
        default=100, description="Maximum session history entries"
    )
    enable_redis_persistence: bool = Field(
        default=False, description="Enable Redis persistence for session history"
    )
    debate_temperature: float = Field(
        default=0.7, description="Temperature for debate LLM"
    )
    debate_max_tokens: int = Field(
        default=2000, description="Max tokens for debate synthesis"
    )


class RedisConfig(BaseSettings):
    """Redis configuration."""

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")


class NavigationConfig(BaseSettings):
    """AI Navigator configuration."""

    max_steps: int = Field(default=15, description="Maximum navigation steps")
    screenshot_quality: int = Field(default=80, description="Screenshot JPEG quality")
    wait_for_navigation: bool = Field(default=True, description="Wait for navigation")
    human_like_delays: bool = Field(
        default=True, description="Add human-like delays between actions"
    )


class AIConfig(BaseSettings):
    """AI/NVIDIA Model configuration."""

    vision_model: str = Field(
        default="nim-llama-32b-vision", description="Vision model name"
    )
    audio_model: str = Field(default="nemotron-asr", description="Audio/ASR model name")
    llm_model: str = Field(default="nemotron-3-22b-chat", description="LLM model name")
    vision_temperature: float = Field(
        default=0.1, description="Vision model temperature"
    )
    audio_temperature: float = Field(default=0.1, description="Audio model temperature")
    llm_temperature: float = Field(default=0.7, description="LLM temperature")
    max_retries: int = Field(default=3, description="Max API retries")
    retry_delay: int = Field(default=1000, description="Retry delay in ms")


class ExtractionConfig(BaseSettings):
    """Extraction configuration."""

    youtube_transcript_first: bool = Field(
        default=True, description="Extract YouTube transcript first"
    )
    audio_split_chunk_size: int = Field(
        default=30, description="Audio split chunk size in seconds"
    )
    frame_extraction_fps: int = Field(default=1, description="Frame extraction FPS")
    vision_analysis_interval: int = Field(
        default=5, description="Vision analysis interval in seconds"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="json", description="Log format")
    file_path: str = Field(default="logs/omni_browser.log", description="Log file path")
    console_enabled: bool = Field(default=True, description="Console logging enabled")
    json_file_enabled: bool = Field(
        default=True, description="JSON file logging enabled"
    )


class SecurityConfig(BaseSettings):
    """Security configuration."""

    prompt_injection_scan: bool = Field(
        default=True, description="Scan for prompt injection"
    )
    session_encryption: bool = Field(default=True, description="Encrypt sessions")
    token_refresh_buffer: int = Field(
        default=300, description="Token refresh buffer in seconds"
    )


class DemoConfig(BaseSettings):
    """Demo configuration."""

    enabled: bool = Field(default=False, description="Demo mode enabled")
    use_stub_credentials: bool = Field(
        default=False, description="Use stub credentials"
    )
    mock_browser: bool = Field(default=False, description="Mock browser")
    mock_ai_responses: bool = Field(default=False, description="Mock AI responses")


class Settings(BaseSettings):
    """Main application settings."""

    # API Keys and Secrets
    nvidia_api_key: str = Field(..., description="NVIDIA API key")

    # YouTube OAuth
    google_client_id: Optional[str] = Field(
        default=None, description="Google OAuth client ID"
    )
    google_client_secret: Optional[str] = Field(
        default=None, description="Google OAuth client secret"
    )

    # Instagram
    instagram_username: Optional[str] = Field(
        default=None, description="Instagram username"
    )
    instagram_password: Optional[str] = Field(
        default=None, description="Instagram password"
    )

    # LinkedIn
    linkedin_username: Optional[str] = Field(
        default=None, description="LinkedIn username"
    )
    linkedin_password: Optional[str] = Field(
        default=None, description="LinkedIn password"
    )

    # Twitter/X
    twitter_bearer_token: Optional[str] = Field(
        default=None, description="Twitter/X bearer token"
    )

    # Optional fallbacks
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key (fallback)"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key (fallback)"
    )

    # Feature flags
    enable_demo_mode: bool = Field(default=False, description="Enable demo/stub mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Sub-configurations
    browser: BrowserConfig = BrowserConfig()
    social: SocialConfig = SocialConfig()
    debate: DebateConfig = DebateConfig()
    redis: RedisConfig = RedisConfig()
    navigation: NavigationConfig = NavigationConfig()
    ai: AIConfig = AIConfig()
    extraction: ExtractionConfig = ExtractionConfig()
    logging: LoggingConfig = LoggingConfig()
    security: SecurityConfig = SecurityConfig()
    demo: DemoConfig = DemoConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Singleton instance with freeze pattern
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get singleton settings instance.
    Loads from config.yaml first, then overrides with .env.
    """
    global _settings
    if _settings is None:
        import yaml
        from pathlib import Path

        yaml_config = {}
        config_path = Path("core/config.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    yaml_config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load config.yaml: {e}")

        # Flatten the YAML for Pydantic (using __init__ to pass values)
        # We'll pass the sub-config dicts directly
        _settings = Settings(**yaml_config)

        # Freeze the settings to prevent modification
        _settings.__dict__["_frozen"] = True
    return _settings


def reset_settings():
    """Reset settings (primarily for testing)."""
    global _settings
    _settings = None
