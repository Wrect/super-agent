"""
Playwright async engine for Omni Browser Agent.
Manages browser lifecycle (launch, context, page pooling) with stealth capabilities.
"""

import asyncio
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from core.logger import get_component_logger
from core.config import get_settings
from core.exceptions import BrowserLaunchError, NavigationTimeoutError


class BrowserEngine:
    """
    Async Playwright engine for browser automation.
    Handles browser launch, context management, and page operations.
    """

    def __init__(self):
        self.logger = get_component_logger("browser")
        self.settings = get_settings()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the browser engine."""
        if self._initialized:
            return

        try:
            self.logger.info("Initializing Playwright browser engine")
            self.playwright = await async_playwright().start()

            # Launch browser based on configuration
            browser_type = self.settings.browser.browser_type
            headless = self.settings.browser.headless

            self.logger.info(f"Launching {browser_type} browser (headless={headless})")

            launch_options = {
                "headless": headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=VizDisplayCompositor",
                ],
            }

            if browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(**launch_options)
            elif browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(**launch_options)
            elif browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(**launch_options)
            else:
                raise BrowserLaunchError(
                    browser_type=browser_type,
                    message=f"Unsupported browser type: {browser_type}",
                )

            self._initialized = True
            self.logger.info("Browser engine initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize browser engine: {e}")
            raise BrowserLaunchError(
                browser_type=self.settings.browser.browser_type, message=str(e)
            )

    async def new_context(self, context_id: str = None) -> BrowserContext:
        """
        Create a new browser context.

        Args:
            context_id: Optional identifier for the context

        Returns:
            BrowserContext instance
        """
        if not self._initialized:
            await self.initialize()

        if context_id is None:
            context_id = f"context_{len(self.contexts)}"

        self.logger.debug(f"Creating new browser context: {context_id}")

        context = await self.browser.new_context(
            viewport={
                "width": self.settings.browser.viewport_width,
                "height": self.settings.browser.viewport_height,
            },
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        # Add stealth scripts to avoid bot detection
        if self.settings.browser.stealth_mode:
            await context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

        self.contexts[context_id] = context
        return context

    async def new_page(self, context_id: str = "default", page_id: str = None) -> Page:
        """
        Create a new page in the specified context.

        Args:
            context_id: Context identifier
            page_id: Optional identifier for the page

        Returns:
            Page instance
        """
        if context_id not in self.contexts:
            await self.new_context(context_id)

        if page_id is None:
            page_id = f"page_{len([p for p in self.pages.values() if p.context.id == self.contexts[context_id].id])}"

        self.logger.debug(f"Creating new page: {page_id} in context: {context_id}")

        page = await self.contexts[context_id].new_page()

        # Set default timeout
        page.set_default_timeout(self.settings.browser.timeout)

        # Store page reference
        full_id = f"{context_id}:{page_id}"
        self.pages[full_id] = page

        return page

    async def navigate(
        self, page: Page, url: str, wait_until: str = "networkidle"
    ) -> None:
        """
        Navigate to a URL.

        Args:
            page: Page instance to navigate
            url: Target URL
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
        """
        try:
            self.logger.info(f"Navigating to: {url}")
            await page.goto(url, wait_until=wait_until)
            self.logger.info(f"Navigation successful: {url}")
        except asyncio.TimeoutError:
            raise NavigationTimeoutError(url=url, timeout=self.settings.browser.timeout)
        except Exception as e:
            self.logger.error(f"Navigation failed to {url}: {e}")
            raise

    async def screenshot(
        self, page: Page, path: str = None, full_page: bool = False
    ) -> bytes:
        """
        Take a screenshot of the page.

        Args:
            page: Page instance
            path: Optional file path to save screenshot
            full_page: Whether to capture full page or viewport only

        Returns:
            Screenshot bytes
        """
        self.logger.debug(f"Taking screenshot (full_page={full_page})")

        screenshot_bytes = await page.screenshot(
            path=path, full_page=full_page, type="png"
        )

        return screenshot_bytes

    async def close_context(self, context_id: str) -> None:
        """
        Close a browser context and all its pages.

        Args:
            context_id: Context identifier to close
        """
        if context_id in self.contexts:
            self.logger.debug(f"Closing context: {context_id}")
            await self.contexts[context_id].close()
            del self.contexts[context_id]

            # Remove associated pages
            pages_to_remove = [
                pid for pid in self.pages.keys() if pid.startswith(f"{context_id}:")
            ]
            for pid in pages_to_remove:
                del self.pages[pid]

    async def close(self) -> None:
        """Close the browser engine and clean up resources."""
        self.logger.info("Closing browser engine")

        # Close all contexts
        for context_id in list(self.contexts.keys()):
            await self.close_context(context_id)

        # Close browser
        if self.browser:
            await self.browser.close()
            self.browser = None

        # Stop playwright
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        self._initialized = False
        self.logger.info("Browser engine closed")


# Global browser engine instance
_browser_engine: Optional[BrowserEngine] = None


async def get_browser_engine() -> BrowserEngine:
    """
    Get singleton browser engine instance.

    Returns:
        BrowserEngine instance
    """
    global _browser_engine
    if _browser_engine is None:
        _browser_engine = BrowserEngine()
        await _browser_engine.initialize()
    return _browser_engine


async def close_browser_engine() -> None:
    """Close the global browser engine instance."""
    global _browser_engine
    if _browser_engine is not None:
        await _browser_engine.close()
        _browser_engine = None
