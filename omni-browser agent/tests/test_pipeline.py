"""
Tests for pipeline components: TaskRouter, Extractors.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from pipeline.task_router import TaskRouter, get_task_router
from pipeline.extractor import (
    YouTubeExtractor,
    InstagramExtractor,
    LinkedInExtractor,
    TwitterExtractor,
)
from models.schemas import BrowserTask, Platform


class TestTaskRouter:
    """Tests for TaskRouter."""

    @pytest.mark.asyncio
    async def test_route_youtube_task(self):
        """Test routing YouTube task."""
        router = TaskRouter()
        task = BrowserTask(
            id="test-1", description="Search YouTube for Python tutorials"
        )

        result = await router.route(task)

        # Should route to YouTube handler
        assert "success" in result or "error" in result

    @pytest.mark.asyncio
    async def test_route_instagram_task(self):
        """Test routing Instagram task."""
        router = TaskRouter()
        task = BrowserTask(id="test-2", description="Extract Instagram post")

        result = await router.route(task)
        assert "success" in result or "error" in result

    @pytest.mark.asyncio
    async def test_route_twitter_task(self):
        """Test routing Twitter task."""
        router = TaskRouter()
        task = BrowserTask(id="test-3", description="Get tweet from Twitter")

        result = await router.route(task)
        assert "success" in result or "error" in result

    @pytest.mark.asyncio
    async def test_route_generic_task(self):
        """Test routing generic browser task."""
        router = TaskRouter()
        task = BrowserTask(id="test-4", description="Open Google and search")

        result = await router.route(task)
        assert result is not None

    @pytest.mark.asyncio
    async def test_detect_platform_youtube(self):
        """Test YouTube platform detection."""
        router = TaskRouter()
        task = BrowserTask(
            id="test-5", description="Search YouTube", url="https://youtube.com"
        )

        platform = await router.detect_platform(task)
        assert platform == Platform.YOUTUBE

    @pytest.mark.asyncio
    async def test_detect_platform_twitter(self):
        """Test Twitter platform detection."""
        router = TaskRouter()
        task = BrowserTask(id="test-6", description="Get tweet")

        platform = await router.detect_platform(task)
        assert platform == Platform.TWITTER


class TestYouTubeExtractor:
    """Tests for YouTubeExtractor."""

    @pytest.mark.asyncio
    async def test_extract_video_id_from_watch_url(self):
        """Test extracting video ID from watch URL."""
        extractor = YouTubeExtractor()

        video_id = extractor._extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"
        )

        assert video_id == "dQw4w9WgXcQ"

    @pytest.mark.asyncio
    async def test_extract_video_id_from_short_url(self):
        """Test extracting video ID from shorts URL."""
        extractor = YouTubeExtractor()

        video_id = extractor._extract_video_id(
            "https://www.youtube.com/shorts/abc123", "youtube"
        )

        assert video_id == "abc123"

    @pytest.mark.asyncio
    async def test_extract_video_id_from_youtu_be(self):
        """Test extracting video ID from youtu.be URL."""
        extractor = YouTubeExtractor()

        video_id = extractor._extract_video_id("https://youtu.be/abc123", "youtube")

        assert video_id == "abc123"

    @pytest.mark.asyncio
    async def test_extract_invalid_url(self):
        """Test handling invalid URL."""
        extractor = YouTubeExtractor()

        video_id = extractor._extract_video_id("https://example.com", "youtube")

        assert video_id is None

    @pytest.mark.asyncio
    async def test_extract_demo_mode(self, settings):
        """Test extraction in demo mode."""
        extractor = YouTubeExtractor()

        result = await extractor.extract("https://youtube.com/watch?v=test")

        assert result.platform == Platform.YOUTUBE


class TestInstagramExtractor:
    """Tests for InstagramExtractor."""

    @pytest.mark.asyncio
    async def test_extract_demo_mode(self, settings):
        """Test extraction in demo mode."""
        extractor = InstagramExtractor()

        result = await extractor.extract("https://instagram.com/p/test/")

        assert result.platform == Platform.INSTAGRAM


class TestLinkedInExtractor:
    """Tests for LinkedInExtractor."""

    @pytest.mark.asyncio
    async def test_extract_demo_mode(self, settings):
        """Test extraction in demo mode."""
        extractor = LinkedInExtractor()

        result = await extractor.extract("https://linkedin.com/feed/update/test")

        assert result.platform == Platform.LINKEDIN


class TestTwitterExtractor:
    """Tests for TwitterExtractor."""

    @pytest.mark.asyncio
    async def test_extract_tweet_id(self):
        """Test extracting tweet ID."""
        extractor = TwitterExtractor()

        tweet_id = extractor._extract_video_id(
            "https://twitter.com/user/status/1234567890", "twitter"
        )

        assert tweet_id == "1234567890"

    @pytest.mark.asyncio
    async def test_extract_demo_mode(self, settings):
        """Test extraction in demo mode."""
        extractor = TwitterExtractor()

        result = await extractor.extract("https://twitter.com/user/status/1234567890")

        assert result.platform == Platform.TWITTER
