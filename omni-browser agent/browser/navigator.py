"""
AI-driven page navigation using NVIDIA LLM.
Given a natural language goal, it captures screenshots, analyzes them with vision models,
and determines the next atomic action to execute.
"""

import asyncio
import io
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from playwright.async_api import Page

from core.logger import get_component_logger
from core.config import get_settings
from pipeline.ai_inference import run_vision_analysis


class NavigationResult:
    """Result of a navigation step."""

    def __init__(
        self,
        action: str,
        selector: Optional[str] = None,
        value: Optional[str] = None,
        reasoning: str = "",
        success: bool = True,
        error: Optional[str] = None,
    ):
        self.action = action
        self.selector = selector
        self.value = value
        self.reasoning = reasoning
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "selector": self.selector,
            "value": self.value,
            "reasoning": self.reasoning,
            "success": self.success,
            "error": self.error,
        }


class AINavigator:
    """
    AI-driven navigator using NVIDIA LLM for browser automation.
    Analyzes page screenshots and determines next actions to achieve goals.
    """

    def __init__(self, page: Page):
        self.logger = get_component_logger("navigator")
        self.settings = get_settings()
        self.page = page
        self.max_steps = self.settings.navigation.max_steps
        self.screenshot_quality = self.settings.navigation.screenshot_quality
        self.human_like_delays = self.settings.navigation.human_like_delays

    async def navigate_to_goal(
        self,
        goal: str,
        max_steps: Optional[int] = None,
        screenshot_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Navigate to achieve a specific goal.

        Args:
            goal: Natural language description of the goal
            max_steps: Optional override for max navigation steps
            screenshot_dir: Optional directory to save screenshots

        Returns:
            Dict containing navigation results, screenshots, and final state
        """
        max_steps = max_steps or self.max_steps
        self.logger.info(f"Starting AI-driven navigation towards goal: {goal}")

        steps_taken = 0
        screenshots = []
        action_history = []
        current_goal = goal

        while steps_taken < max_steps:
            self.logger.debug(f"Navigation step {steps_taken + 1}/{max_steps}")

            # Take screenshot
            screenshot_bytes = await self.page.screenshot(type="png", full_page=False)

            if screenshot_dir:
                screenshot_path = screenshot_dir / f"step_{steps_taken}.png"
                screenshot_path.write_bytes(screenshot_bytes)
                screenshots.append(str(screenshot_path))

            # Analyze screenshot with NVIDIA vision model
            try:
                vision_result = await run_vision_analysis(
                    image_bytes=screenshot_bytes,
                    prompt=f"""
                    You are a browser automation AI. Analyze this screenshot and determine 
                    the next action to take to achieve the following goal:
                    
                    GOAL: {current_goal}
                    
                    Available actions:
                    - click: Click on an element (provide CSS selector)
                    - fill: Type text into an input (provide CSS selector and text)
                    - scroll: Scroll the page (up, down, or amount in pixels)
                    - hover: Hover over an element (provide CSS selector)
                    - wait: Wait for a specific time (in seconds)
                    - navigate: Navigate to a URL
                    - extract: Extract content from the page
                    - done: Goal has been achieved
                    
                    Respond with a JSON object containing:
                    {{
                        "action": "action_name",
                        "selector": "css_selector (if applicable)",
                        "value": "value (if applicable)",
                        "reasoning": "explanation of why this action was chosen"
                    }}
                    """,
                )

                # Parse the vision model's response
                action_data = self._parse_action_response(vision_result)

                if action_data["action"] == "done":
                    self.logger.info("Goal achieved!")
                    return {
                        "success": True,
                        "goal": goal,
                        "steps_taken": steps_taken,
                        "screenshots": screenshots,
                        "action_history": action_history,
                        "message": "Goal achieved successfully",
                    }

                # Execute the action
                result = await self._execute_action(action_data)
                action_history.append(action_data)

                if not result.success:
                    self.logger.warning(f"Action failed: {result.error}")
                    # Continue trying with next step

                # Add human-like delay between actions
                if self.human_like_delays:
                    await asyncio.sleep(0.5 + (hash(str(steps_taken)) % 1000) / 1000)

            except Exception as e:
                self.logger.error(f"Vision analysis failed: {e}")
                # Try to extract content as fallback
                action_history.append({"action": "extract", "error": str(e)})

            steps_taken += 1

        # Max steps reached
        self.logger.warning(f"Max steps ({max_steps}) reached without achieving goal")

        # Try to extract whatever content is available
        try:
            page_content = await self.page.content()
        except Exception:
            page_content = ""

        return {
            "success": False,
            "goal": goal,
            "steps_taken": steps_taken,
            "screenshots": screenshots,
            "action_history": action_history,
            "message": f"Max steps ({max_steps}) reached",
            "page_content": page_content[:1000],  # Truncate content
        }

    def _parse_action_response(self, vision_result: str) -> Dict[str, Any]:
        """Parse the vision model's response into action data."""
        try:
            # Try to extract JSON from the response
            # The response might contain JSON wrapped in markdown code blocks
            import re

            # Look for JSON in the response
            json_match = re.search(r"\{[^{}]*\}", vision_result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # Fallback: try to parse the entire response as JSON
            return json.loads(vision_result)

        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.warning(f"Failed to parse vision response: {e}")
            # Default to extract action
            return {
                "action": "extract",
                "reasoning": "Could not parse vision response, extracting content",
            }

    async def _execute_action(self, action_data: Dict[str, Any]) -> NavigationResult:
        """Execute a browser action based on action data."""
        action = action_data.get("action", "")
        selector = action_data.get("selector")
        value = action_data.get("value")
        reasoning = action_data.get("reasoning", "")

        self.logger.debug(
            f"Executing action: {action} (selector: {selector}, value: {value})"
        )

        try:
            if action == "click":
                if not selector:
                    return NavigationResult(
                        action=action,
                        success=False,
                        error="No selector provided for click action",
                    )
                await self.page.click(selector)

            elif action == "fill":
                if not selector or not value:
                    return NavigationResult(
                        action=action,
                        success=False,
                        error="No selector or value provided for fill action",
                    )
                await self.page.fill(selector, value)

            elif action == "scroll":
                if value in ["up", "down"]:
                    scroll_amount = 500 if value == "down" else -500
                    await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                else:
                    # Try to parse as pixel amount
                    try:
                        scroll_pixels = int(value)
                        await self.page.evaluate(f"window.scrollBy(0, {scroll_pixels})")
                    except ValueError:
                        await self.page.evaluate("window.scrollBy(0, 500)")

            elif action == "hover":
                if not selector:
                    return NavigationResult(
                        action=action,
                        success=False,
                        error="No selector provided for hover action",
                    )
                await self.page.hover(selector)

            elif action == "wait":
                wait_time = 1  # Default 1 second
                try:
                    wait_time = float(value)
                except (TypeError, ValueError):
                    pass
                await asyncio.sleep(wait_time)

            elif action == "navigate":
                if not value:
                    return NavigationResult(
                        action=action,
                        success=False,
                        error="No URL provided for navigate action",
                    )
                await self.page.goto(value, wait_until="networkidle")

            elif action == "extract":
                # Just return success - content extraction happens later
                pass

            else:
                self.logger.warning(f"Unknown action: {action}")
                return NavigationResult(
                    action=action, success=False, error=f"Unknown action: {action}"
                )

            return NavigationResult(
                action=action,
                selector=selector,
                value=value,
                reasoning=reasoning,
                success=True,
            )

        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
            return NavigationResult(action=action, success=False, error=str(e))
