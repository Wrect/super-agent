"""
CrewAI agent definitions for Omni Browser Agent.
Defines the OmniBrowserAgent that wraps all tools and orchestrates task execution.
"""

from typing import List, Dict, Any, Optional

from core.logger import get_component_logger
from core.config import get_settings


class OmniBrowserAgent:
    """
    Main browser agent that orchestrates all tools and capabilities.
    Wraps the TaskRouter for intent-based task execution.
    """

    def __init__(self):
        self.logger = get_component_logger("crew")
        self.settings = get_settings()
        self.name = "OmniBrowserAgent"
        self.description = "Autonomous browser agent that can execute any browser task and extract content from social media platforms"

    async def execute_task(self, task_description: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a browser task.

        Args:
            task_description: Natural language task description
            **kwargs: Additional task parameters

        Returns:
            Dict containing task results
        """
        from models.schemas import BrowserTask, Platform
        import uuid

        # Create task
        task = BrowserTask(id=str(uuid.uuid4()), description=task_description, **kwargs)

        self.logger.info(f"Executing task: {task_description}")

        # Route to appropriate handler
        from pipeline.task_router import get_task_router

        router = get_task_router()
        result = await router.route(task)

        return result

    async def extract_content(
        self, url: str, platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract content from a URL.

        Args:
            url: URL to extract from
            platform: Optional platform hint

        Returns:
            Dict containing extraction results
        """
        from models.schemas import BrowserTask, Platform
        import uuid

        # Detect platform if not provided
        if not platform:
            url_lower = url.lower()
            if "youtube" in url_lower:
                platform = "youtube"
            elif "instagram" in url_lower:
                platform = "instagram"
            elif "linkedin" in url_lower:
                platform = "linkedin"
            elif "twitter" in url_lower or "x.com" in url_lower:
                platform = "twitter"

        task = BrowserTask(
            id=str(uuid.uuid4()), description=f"Extract content from {url}", url=url
        )

        from pipeline.task_router import get_task_router

        router = get_task_router()
        result = await router.route(task)

        return result

    async def browse_and_research(
        self, query: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Browse and research information.

        Args:
            query: Research query
            max_results: Maximum results to return

        Returns:
            Dict containing research results
        """
        from models.schemas import BrowserTask
        import uuid

        task = BrowserTask(
            id=str(uuid.uuid4()), description=f"Research: {query}", max_steps=20
        )

        from pipeline.task_router import get_task_router

        router = get_task_router()
        result = await router.route(task)

        return result

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return {
            "name": self.name,
            "description": self.description,
            "supported_platforms": [
                "youtube",
                "instagram",
                "linkedin",
                "twitter",
                "web",
            ],
            "features": [
                "AI-driven browser navigation",
                "Social media content extraction",
                "Web research and browsing",
                "Transcript extraction (YouTube)",
                "Prompt history debate engine",
                "Session memory with LRU cache",
            ],
        }


# Global agent instance
_omni_browser_agent: Optional[OmniBrowserAgent] = None


def get_omni_browser_agent() -> OmniBrowserAgent:
    """Get singleton OmniBrowserAgent instance."""
    global _omni_browser_agent
    if _omni_browser_agent is None:
        _omni_browser_agent = OmniBrowserAgent()
    return _omni_browser_agent
