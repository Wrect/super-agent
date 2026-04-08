"""
Task router for Omni Browser Agent.
Intent classifier that parses user's natural language task and routes to appropriate handler.
"""

import re
from typing import Dict, Any, Optional, List

from core.logger import get_component_logger
from core.config import get_settings
from models.schemas import Platform, BrowserTask


class TaskHandler:
    """Base class for task handlers."""

    def __init__(self, name: str):
        self.name = name
        self.logger = get_component_logger(f"router.{name}")

    async def can_handle(self, task: BrowserTask) -> bool:
        """Check if this handler can handle the task."""
        raise NotImplementedError

    async def execute(self, task: BrowserTask) -> Dict[str, Any]:
        """Execute the task."""
        raise NotImplementedError


class BrowserTaskHandler(TaskHandler):
    """Generic browser automation handler with platform-aware navigation."""

    # Map keywords in user descriptions to starting URLs
    PLATFORM_URL_MAP = {
        "instagram": "https://www.instagram.com/",
        "youtube": "https://www.youtube.com/",
        "linkedin": "https://www.linkedin.com/",
        "twitter": "https://x.com/",
        "x.com": "https://x.com/",
        "google": "https://www.google.com/",
        "facebook": "https://www.facebook.com/",
    }

    def __init__(self):
        super().__init__("browser")

    async def can_handle(self, task: BrowserTask) -> bool:
        """Can handle generic browser tasks."""
        return True

    def _detect_start_url(self, description: str) -> Optional[str]:
        """Detect the starting URL from the task description."""
        desc_lower = description.lower()
        for keyword, url in self.PLATFORM_URL_MAP.items():
            if keyword in desc_lower:
                return url
        return None

    async def _inject_cookies(self, context, platform: str) -> bool:
        """Load session cookies from auth manager and inject them into the browser context."""
        try:
            from auth.manager import get_auth_manager
            import json
            from pathlib import Path

            session_file = Path(f"data/tokens/{platform}_session.json")
            if not session_file.exists():
                self.logger.warning(f"No session file found for {platform}")
                return False

            session_data = json.loads(session_file.read_text())
            cookies = session_data.get("cookies", [])

            if cookies:
                await context.add_cookies(cookies)
                self.logger.info(f"Injected {len(cookies)} cookies for {platform}")
                return True
            else:
                self.logger.warning(f"Session file for {platform} has no cookies")
                return False
        except Exception as e:
            self.logger.error(f"Failed to inject cookies for {platform}: {e}")
            return False

    async def execute(self, task: BrowserTask) -> Dict[str, Any]:
        """Execute generic browser task with platform-aware cookie injection."""
        self.logger.info(f"Executing browser task: {task.description}")

        from browser.engine import get_browser_engine

        browser_engine = await get_browser_engine()
        context = await browser_engine.new_context("task")

        # Detect platform and inject cookies BEFORE creating a page
        start_url = task.url or self._detect_start_url(task.description)
        desc_lower = task.description.lower()

        if "instagram" in desc_lower:
            await self._inject_cookies(context, "instagram")
        elif "youtube" in desc_lower:
            await self._inject_cookies(context, "youtube")
        elif "linkedin" in desc_lower:
            await self._inject_cookies(context, "linkedin")

        page = await browser_engine.new_page("task", f"page_{task.id}")

        if start_url:
            self.logger.info(f"Navigating to detected start URL: {start_url}")
            try:
                await page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
                # Wait a bit for the page to settle after cookie injection
                import asyncio
                await asyncio.sleep(3)
            except Exception as e:
                self.logger.warning(f"Initial navigation had an issue: {e}")

        # Now try AI-driven navigation
        try:
            from browser.navigator import AINavigator
            navigator = AINavigator(page)
            result = await navigator.navigate_to_goal(
                goal=task.description, max_steps=task.max_steps
            )
            return result
        except Exception as e:
            self.logger.error(f"AI Navigator failed: {e}")
            # Fallback: take a screenshot and return current page state
            try:
                screenshot = await page.screenshot(type="png")
                from pathlib import Path
                ss_path = Path("data/screenshots")
                ss_path.mkdir(parents=True, exist_ok=True)
                ss_file = ss_path / f"fallback_{task.id}.png"
                ss_file.write_bytes(screenshot)
                page_url = page.url
                page_title = await page.title()
                return {
                    "success": False,
                    "error": f"AI Navigator failed: {str(e)}",
                    "current_url": page_url,
                    "page_title": page_title,
                    "screenshot": str(ss_file),
                    "message": "Browser opened and navigated but AI navigator could not complete the goal. Screenshot saved.",
                }
            except Exception as inner_e:
                return {"success": False, "error": f"Complete failure: {str(e)} -> {str(inner_e)}"}


class YouTubeExtractorHandler(TaskHandler):
    """YouTube content extraction handler."""

    def __init__(self):
        super().__init__("youtube")

    async def can_handle(self, task: BrowserTask) -> bool:
        """Check if task is for YouTube extraction."""
        if not task.url:
            return False
        task_text = task.description.lower() + " " + str(task.url).lower()
        return "youtube" in task_text or "youtu.be" in task_text

    async def execute(self, task: BrowserTask) -> Dict[str, Any]:
        """Execute YouTube extraction."""
        self.logger.info(f"Extracting YouTube content: {task.description}")

        from pipeline.extractor import YouTubeExtractor

        extractor = YouTubeExtractor()

        if task.url:
            result = await extractor.extract(str(task.url))
            return {"success": True, "result": result}

        return {"success": False, "error": "No URL provided"}


class InstagramExtractorHandler(TaskHandler):
    """Instagram content extraction handler."""

    def __init__(self):
        super().__init__("instagram")

    async def can_handle(self, task: BrowserTask) -> bool:
        """Check if task is for Instagram extraction."""
        if not task.url:
            return False
        task_text = task.description.lower() + " " + str(task.url).lower()
        return "instagram" in task_text or "ig" in task_text

    async def execute(self, task: BrowserTask) -> Dict[str, Any]:
        """Execute Instagram extraction."""
        self.logger.info(f"Extracting Instagram content: {task.description}")

        from pipeline.extractor import InstagramExtractor

        extractor = InstagramExtractor()

        if task.url:
            result = await extractor.extract(str(task.url))
            return {"success": True, "result": result}

        return {"success": False, "error": "No URL provided"}


class LinkedInExtractorHandler(TaskHandler):
    """LinkedIn content extraction handler."""

    def __init__(self):
        super().__init__("linkedin")

    async def can_handle(self, task: BrowserTask) -> bool:
        """Check if task is for LinkedIn extraction."""
        if not task.url:
            return False
        task_text = task.description.lower() + " " + str(task.url).lower()
        return "linkedin" in task_text or "li" in task_text

    async def execute(self, task: BrowserTask) -> Dict[str, Any]:
        """Execute LinkedIn extraction."""
        self.logger.info(f"Extracting LinkedIn content: {task.description}")

        from pipeline.extractor import LinkedInExtractor

        extractor = LinkedInExtractor()

        if task.url:
            result = await extractor.extract(str(task.url))
            return {"success": True, "result": result}

        return {"success": False, "error": "No URL provided"}


class TwitterExtractorHandler(TaskHandler):
    """Twitter/X content extraction handler."""

    def __init__(self):
        super().__init__("twitter")

    async def can_handle(self, task: BrowserTask) -> bool:
        """Check if task is for Twitter/X extraction."""
        if not task.url:
            return False
        task_text = task.description.lower() + " " + str(task.url).lower()
        return "twitter" in task_text or "x.com" in task_text or "tweet" in task_text

    async def execute(self, task: BrowserTask) -> Dict[str, Any]:
        """Execute Twitter extraction."""
        self.logger.info(f"Extracting Twitter content: {task.description}")

        from pipeline.extractor import TwitterExtractor

        extractor = TwitterExtractor()

        if task.url:
            result = await extractor.extract(str(task.url))
            return {"success": True, "result": result}

        return {"success": False, "error": "No URL provided"}


class WebResearchHandler(TaskHandler):
    """Web research handler for general browsing."""

    def __init__(self):
        super().__init__("web_research")

    async def can_handle(self, task: BrowserTask) -> bool:
        """Check if task is a web research task."""
        task_text = task.description.lower()
        research_keywords = ["search", "find", "research", "lookup", "browse"]
        return any(kw in task_text for kw in research_keywords)

    async def execute(self, task: BrowserTask) -> Dict[str, Any]:
        """Execute web research task."""
        self.logger.info(f"Executing web research: {task.description}")

        from browser.engine import get_browser_engine
        from browser.navigator import AINavigator
        from browser.actions import BrowserActions

        browser_engine = await get_browser_engine()
        context = await browser_engine.new_context("research")
        page = await browser_engine.new_page("research", f"page_{task.id}")

        # Navigate to search engine
        await page.goto("https://www.google.com")

        actions = BrowserActions(page)

        # Extract search query from task description
        query = self._extract_search_query(task.description)

        # Fill search box and search
        await actions.fill('textarea[name="q"]', query)
        await actions.press_key("Enter")

        # Wait for results
        await actions.wait_for("#search", state="visible")

        # Extract results
        results = await self._extract_search_results(page)

        await browser_engine.close_context("research")

        return {"success": True, "query": query, "results": results}

    def _extract_search_query(self, description: str) -> str:
        """Extract search query from task description."""
        # Remove common search keywords
        cleaned = re.sub(
            r"^(search|find|research|lookup|browse)\s+(for|)\s*",
            "",
            description,
            flags=re.IGNORECASE,
        )
        return cleaned.strip()

    async def _extract_search_results(self, page) -> List[Dict[str, str]]:
        """Extract search results from page."""
        return await page.evaluate("""
            () => {
                const results = [];
                const items = document.querySelectorAll('#search .g');
                items.forEach((item, index) => {
                    if (index >= 10) return;  // Limit to top 10
                    const titleEl = item.querySelector('h3');
                    const linkEl = item.querySelector('a');
                    const snippetEl = item.querySelector('.VwiC3b');
                    if (titleEl && linkEl) {
                        results.push({
                            title: titleEl.innerText,
                            url: linkEl.href,
                            snippet: snippetEl ? snippetEl.innerText : ''
                        });
                    }
                });
                return results;
            }
        """)


class TaskRouter:
    """
    Intent classifier and task router.
    Routes tasks to appropriate handlers based on task content.
    """

    def __init__(self):
        self.logger = get_component_logger("router")
        self.handlers: List[TaskHandler] = [
            YouTubeExtractorHandler(),
            InstagramExtractorHandler(),
            LinkedInExtractorHandler(),
            TwitterExtractorHandler(),
            WebResearchHandler(),
            BrowserTaskHandler(),  # Default handler
        ]

    async def route(self, task: BrowserTask) -> Dict[str, Any]:
        """
        Route task to appropriate handler.

        Args:
            task: BrowserTask to route

        Returns:
            Dict containing execution results
        """
        self.logger.info(f"Routing task: {task.description}")

        # Try each handler in order
        for handler in self.handlers:
            try:
                if await handler.can_handle(task):
                    self.logger.info(f"Routing to handler: {handler.name}")
                    result = await handler.execute(task)
                    return result
            except Exception as e:
                self.logger.warning(f"Handler {handler.name} failed: {e}")
                continue

        # Should never reach here due to BrowserTaskHandler being last
        return {"success": False, "error": "No handler could process the task"}

    async def detect_platform(self, task: BrowserTask) -> Optional[Platform]:
        """Detect target platform from task."""
        task_text = task.description.lower() + " " + (str(task.url) if task.url else "")

        if "youtube" in task_text:
            return Platform.YOUTUBE
        elif "instagram" in task_text or "ig" in task_text:
            return Platform.INSTAGRAM
        elif "linkedin" in task_text:
            return Platform.LINKEDIN
        elif "twitter" in task_text or "x.com" in task_text:
            return Platform.TWITTER

        return None


# Global router instance
_task_router: Optional[TaskRouter] = None


def get_task_router() -> TaskRouter:
    """Get singleton task router instance."""
    global _task_router
    if _task_router is None:
        _task_router = TaskRouter()
    return _task_router
