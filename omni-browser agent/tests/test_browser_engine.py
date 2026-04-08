"""
Tests for browser engine.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from browser.engine import BrowserEngine, get_browser_engine, close_browser_engine
from browser.navigator import AINavigator
from browser.actions import BrowserActions
from core.exceptions import BrowserLaunchError, NavigationTimeoutError


class TestBrowserEngine:
    """Tests for BrowserEngine."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test browser engine initialization."""
        engine = BrowserEngine()

        # Engine should not be initialized yet
        assert engine._initialized is False

    @pytest.mark.asyncio
    async def test_new_context(self):
        """Test creating new browser context."""
        engine = BrowserEngine()

        with patch("browser.engine.async_playwright") as mock_playwright:
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()

            mock_pw.start = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_playwright.return_value = mock_pw

            engine.playwright = mock_pw
            engine.browser = mock_browser
            engine._initialized = True

            context = await engine.new_context("test-context")

            assert context is not None

    @pytest.mark.asyncio
    async def test_new_page(self):
        """Test creating new page."""
        engine = BrowserEngine()

        with patch("browser.engine.async_playwright") as mock_playwright:
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_pw.start = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_playwright.return_value = mock_pw

            engine.playwright = mock_pw
            engine.browser = mock_browser
            engine._initialized = True

            # Add context first
            engine.contexts["test"] = mock_context

            page = await engine.new_page("test", "test-page")

            assert page is not None

    @pytest.mark.asyncio
    async def test_close_context(self):
        """Test closing browser context."""
        engine = BrowserEngine()

        mock_context = MagicMock()
        mock_context.close = AsyncMock()

        engine.contexts["test-context"] = mock_context
        engine.pages["test-context:test-page"] = MagicMock()

        await engine.close_context("test-context")

        assert "test-context" not in engine.contexts
        assert "test-context:test-page" not in engine.pages

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing browser engine."""
        engine = BrowserEngine()

        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()

        engine.browser = mock_browser
        engine.playwright = mock_playwright
        engine._initialized = True

        await engine.close()

        assert engine._initialized is False


class TestAINavigator:
    """Tests for AINavigator."""

    @pytest.mark.asyncio
    async def test_parse_action_response(self):
        """Test parsing action response from vision model."""
        mock_page = MagicMock()
        navigator = AINavigator(mock_page)

        vision_result = (
            '{"action": "click", "selector": ".btn", "reasoning": "Found button"}'
        )

        action_data = navigator._parse_action_response(vision_result)

        assert action_data["action"] == "click"
        assert action_data["selector"] == ".btn"

    @pytest.mark.asyncio
    async def test_parse_invalid_response(self):
        """Test handling invalid vision response."""
        mock_page = MagicMock()
        navigator = AINavigator(mock_page)

        vision_result = "not valid json"

        action_data = navigator._parse_action_response(vision_result)

        # Should default to extract action
        assert action_data["action"] == "extract"


class TestBrowserActions:
    """Tests for BrowserActions."""

    @pytest.mark.asyncio
    async def test_click(self):
        """Test click action."""
        mock_page = MagicMock()
        mock_page.click = AsyncMock()

        actions = BrowserActions(mock_page)
        result = await actions.click(".btn")

        assert result is True
        mock_page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_failure(self):
        """Test click action failure."""
        mock_page = MagicMock()
        mock_page.click = AsyncMock(side_effect=Exception("Element not found"))

        actions = BrowserActions(mock_page)
        result = await actions.click(".nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_fill(self):
        """Test fill action."""
        mock_page = MagicMock()
        mock_page.fill = AsyncMock()

        actions = BrowserActions(mock_page)
        result = await actions.fill("input[name='q']", "test query")

        assert result is True

    @pytest.mark.asyncio
    async def test_scroll(self):
        """Test scroll action."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock()

        actions = BrowserActions(mock_page)
        result = await actions.scroll("down")

        assert result is True

    @pytest.mark.asyncio
    async def test_navigate(self):
        """Test navigate action."""
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        actions = BrowserActions(mock_page)
        result = await actions.navigate("https://example.com")

        assert result is True
        mock_page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_screenshot(self):
        """Test screenshot action."""
        mock_page = MagicMock()
        mock_page.screenshot = AsyncMock(b"fake_image_data")

        actions = BrowserActions(mock_page)
        result = await actions.screenshot()

        assert result == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_extract_text(self):
        """Test text extraction."""
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value="Page text")

        actions = BrowserActions(mock_page)
        result = await actions.extract_text(all_pages=True)

        assert result == "Page text"

    @pytest.mark.asyncio
    async def test_press_key(self):
        """Test key press."""
        mock_page = MagicMock()
        mock_page.keyboard.press = AsyncMock()

        actions = BrowserActions(mock_page)
        result = await actions.press_key("Enter")

        assert result is True

    @pytest.mark.asyncio
    async def test_type_text(self):
        """Test type text."""
        mock_page = MagicMock()
        mock_page.keyboard.type = AsyncMock()

        actions = BrowserActions(mock_page)
        result = await actions.type_text("Hello world")

        assert result is True
