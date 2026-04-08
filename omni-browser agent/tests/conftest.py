"""
Pytest configuration and shared fixtures for Omni Browser Agent tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from core.config import Settings, reset_settings
from models.schemas import (
    BrowserTask,
    TaskResult,
    TaskStatus,
    Platform,
    YouTubeVideo,
    SessionHistory,
    DebateContext,
)


@pytest.fixture
def settings():
    """Provide test settings."""
    reset_settings()
    settings = Settings(
        nvidia_api_key="test_key", enable_demo_mode=True, log_level="DEBUG"
    )
    return settings


@pytest.fixture
def browser_task():
    """Provide sample browser task."""
    return BrowserTask(
        id="test-task-1",
        description="Search YouTube for Python tutorials",
        platform=Platform.YOUTUBE,
        max_steps=10,
        headless=True,
    )


@pytest.fixture
def task_result():
    """Provide sample task result."""
    return TaskResult(
        task_id="test-task-1",
        status=TaskStatus.COMPLETED,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        output={"results": ["video1", "video2"]},
    )


@pytest.fixture
def youtube_video():
    """Provide sample YouTube video."""
    return YouTubeVideo(
        post_id="abc123",
        url="https://youtube.com/watch?v=abc123",
        timestamp=datetime.utcnow(),
        author="TestChannel",
        content="Test video description",
        title="Test Video",
        duration=600,
        view_count=1000,
        transcript="Test transcript",
    )


@pytest.fixture
def mock_playwright():
    """Mock Playwright browser."""
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    # Setup async mock methods
    mock_page.goto = AsyncMock()
    mock_page.screenshot = AsyncMock(b"fake_screenshot")
    mock_page.click = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html>Test page</html>")

    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    return mock_browser


@pytest.fixture
def session_history_entry(browser_task, task_result):
    """Provide sample session history entry."""
    return SessionHistory(
        id="test-history-1",
        timestamp=datetime.utcnow(),
        task=browser_task,
        result=task_result,
    )


@pytest.fixture
def debate_context():
    """Provide sample debate context."""
    return DebateContext(
        prompt_a="Search for Python tutorials from popular channels",
        prompt_b="Find recent Python asyncio videos",
        intent_a="Find Python tutorials from popular YouTube channels",
        intent_b="Find recent Python asyncio tutorial videos",
        conflicts=["Channel filter not in B"],
        overlaps=["Both want Python YouTube videos"],
        priority_decision="B",
    )


@pytest.fixture
def mock_nvidia_client():
    """Mock NVIDIA API client."""
    mock = MagicMock()
    mock.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[
                Mock(message=Mock(content='{"action": "extract", "reasoning": "Test"}'))
            ]
        )
    )
    return mock


@pytest.fixture
def sample_youtube_url():
    """Sample YouTube URL for testing."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def sample_instagram_url():
    """Sample Instagram URL for testing."""
    return "https://www.instagram.com/p/test/"


@pytest.fixture
def sample_twitter_url():
    """Sample Twitter URL for testing."""
    return "https://twitter.com/user/status/123456789"


@pytest.fixture(autouse=True)
def reset_event_loop():
    """Reset event loop after each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()
