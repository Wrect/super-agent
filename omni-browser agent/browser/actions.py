"""
Atomic browser actions for Omni Browser Agent.
Provides low-level primitives for browser interaction.
"""

import asyncio
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from playwright.async_api import Page, Locator, expect

from core.logger import get_component_logger
from core.config import get_settings


class BrowserActions:
    """
    Atomic browser action primitives.
    Provides low-level functions for click, fill, scroll, hover, wait, etc.
    """

    def __init__(self, page: Page):
        self.logger = get_component_logger("actions")
        self.settings = get_settings()
        self.page = page

    async def click(self, selector: str, timeout: Optional[int] = None) -> bool:
        """
        Click on an element.

        Args:
            selector: CSS selector for the element
            timeout: Optional timeout in milliseconds

        Returns:
            True if click was successful
        """
        try:
            self.logger.debug(f"Clicking element: {selector}")
            timeout = timeout or self.settings.browser.timeout
            await self.page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.error(f"Click failed for {selector}: {e}")
            return False

    async def fill(
        self, selector: str, value: str, timeout: Optional[int] = None
    ) -> bool:
        """
        Fill an input field with text.

        Args:
            selector: CSS selector for the input
            value: Text value to fill
            timeout: Optional timeout in milliseconds

        Returns:
            True if fill was successful
        """
        try:
            self.logger.debug(f"Filling {selector} with: {value[:20]}...")
            timeout = timeout or self.settings.browser.timeout
            await self.page.fill(selector, value, timeout=timeout)
            return True
        except Exception as e:
            self.logger.error(f"Fill failed for {selector}: {e}")
            return False

    async def scroll(
        self,
        direction: str = "down",
        amount: Optional[int] = None,
        selector: Optional[str] = None,
    ) -> bool:
        """
        Scroll the page or an element.

        Args:
            direction: 'up', 'down', 'top', 'bottom', or 'element'
            amount: Pixel amount to scroll (for direction scrolling)
            selector: Optional CSS selector for element to scroll

        Returns:
            True if scroll was successful
        """
        try:
            if selector:
                self.logger.debug(f"Scrolling element: {selector}")
                await self.page.locator(selector).scroll_into_view_if_needed()
            elif direction == "top":
                await self.page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                await self.page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
            else:
                amount = amount or 500
                scroll_amount = -amount if direction == "up" else amount
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")

            return True
        except Exception as e:
            self.logger.error(f"Scroll failed: {e}")
            return False

    async def hover(self, selector: str, timeout: Optional[int] = None) -> bool:
        """
        Hover over an element.

        Args:
            selector: CSS selector for the element
            timeout: Optional timeout in milliseconds

        Returns:
            True if hover was successful
        """
        try:
            self.logger.debug(f"Hovering over: {selector}")
            timeout = timeout or self.settings.browser.timeout
            await self.page.hover(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.error(f"Hover failed for {selector}: {e}")
            return False

    async def wait_for(
        self,
        selector: Optional[str] = None,
        state: str = "visible",
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Wait for an element or condition.

        Args:
            selector: CSS selector for the element
            state: 'visible', 'hidden', 'attached', 'detached'
            timeout: Optional timeout in milliseconds

        Returns:
            True if condition was met
        """
        try:
            timeout = timeout or self.settings.browser.timeout

            if selector:
                self.logger.debug(f"Waiting for {selector} to be {state}")
                locator = self.page.locator(selector)
                if state == "visible":
                    await locator.wait_for(state="visible", timeout=timeout)
                elif state == "hidden":
                    await locator.wait_for(state="hidden", timeout=timeout)
                elif state == "attached":
                    await locator.wait_for(state="attached", timeout=timeout)
                elif state == "detached":
                    await locator.wait_for(state="detached", timeout=timeout)
            else:
                # Just wait a bit
                await asyncio.sleep(1)

            return True
        except Exception as e:
            self.logger.error(f"Wait failed: {e}")
            return False

    async def navigate(self, url: str, wait_until: str = "networkidle") -> bool:
        """
        Navigate to a URL.

        Args:
            url: Target URL
            wait_until: Wait condition

        Returns:
            True if navigation was successful
        """
        try:
            self.logger.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until=wait_until)
            return True
        except Exception as e:
            self.logger.error(f"Navigation failed to {url}: {e}")
            return False

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
        selector: Optional[str] = None,
    ) -> bytes:
        """
        Take a screenshot.

        Args:
            path: Optional file path to save screenshot
            full_page: Whether to capture full page
            selector: Optional selector for element to capture

        Returns:
            Screenshot bytes
        """
        try:
            if selector:
                self.logger.debug(f"Taking screenshot of element: {selector}")
                element = self.page.locator(selector)
                return await element.screenshot(path=path, type="png")
            else:
                self.logger.debug(f"Taking screenshot (full_page={full_page})")
                return await self.page.screenshot(
                    path=path, full_page=full_page, type="png"
                )
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            raise

    async def extract_text(
        self, selector: Optional[str] = None, all_pages: bool = False
    ) -> str:
        """
        Extract text from the page or element.

        Args:
            selector: Optional CSS selector for element
            all_pages: Whether to extract all visible text

        Returns:
            Extracted text content
        """
        try:
            if selector:
                self.logger.debug(f"Extracting text from: {selector}")
                return await self.page.locator(selector).inner_text()
            elif all_pages:
                self.logger.debug("Extracting all text from page")
                return await self.page.evaluate("""
                    () => {
                        return document.body.innerText;
                    }
                """)
            else:
                return await self.page.content()
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            return ""

    async def extract_attributes(
        self, selector: str, attributes: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Extract attributes from elements.

        Args:
            selector: CSS selector for elements
            attributes: List of attribute names to extract

        Returns:
            List of dicts containing attribute values
        """
        try:
            self.logger.debug(f"Extracting attributes from: {selector}")

            results = await self.page.evaluate(
                f"""
                (selector, attrs) => {{
                    const elements = document.querySelectorAll(selector);
                    return Array.from(elements).map(el => {{
                        const result = {{}};
                        attrs.forEach(attr => {{
                            result[attr] = el.getAttribute(attr);
                        }});
                        return result;
                    }});
                }}
            """,
                selector,
                attributes,
            )

            return results
        except Exception as e:
            self.logger.error(f"Attribute extraction failed: {e}")
            return []

    async def download_file(
        self, selector: str, download_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Download a file by clicking on a download link/button.

        Args:
            selector: CSS selector for the download element
            download_path: Optional path to save the file

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            self.logger.debug(f"Downloading file from: {selector}")

            async with self.page.expect_download() as download_info:
                await self.page.click(selector)

            download = await download_info.value
            download_path = download_path or os.path.join(
                "downloads", download.suggested_filename
            )

            Path(download_path).parent.mkdir(parents=True, exist_ok=True)
            await download.save_as(download_path)

            self.logger.info(f"File downloaded to: {download_path}")
            return download_path

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return None

    async def select_option(
        self, selector: str, value: str, by_value: bool = True
    ) -> bool:
        """
        Select an option from a dropdown.

        Args:
            selector: CSS selector for the select element
            value: Value to select
            by_value: Whether to select by value (vs by label)

        Returns:
            True if selection was successful
        """
        try:
            self.logger.debug(f"Selecting {value} from {selector}")

            if by_value:
                await self.page.select_option(selector, value=value)
            else:
                await self.page.select_option(selector, label=value)

            return True
        except Exception as e:
            self.logger.error(f"Select option failed: {e}")
            return False

    async def press_key(self, key: str) -> bool:
        """
        Press a keyboard key.

        Args:
            key: Key name (e.g., 'Enter', 'Escape', 'Control+a')

        Returns:
            True if key press was successful
        """
        try:
            self.logger.debug(f"Pressing key: {key}")
            await self.page.keyboard.press(key)
            return True
        except Exception as e:
            self.logger.error(f"Key press failed: {e}")
            return False

    async def type_text(self, text: str, delay: int = 0) -> bool:
        """
        Type text with optional character delay.

        Args:
            text: Text to type
            delay: Delay between characters in ms

        Returns:
            True if typing was successful
        """
        try:
            self.logger.debug(f"Typing text: {text[:20]}...")
            await self.page.keyboard.type(text, delay=delay)
            return True
        except Exception as e:
            self.logger.error(f"Type text failed: {e}")
            return False
