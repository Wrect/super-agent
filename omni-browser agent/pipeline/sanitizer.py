"""
Prompt injection sanitizer for Omni Browser Agent.
Sanitizes scraped text before passing to LLM context.
"""

import re
from typing import Dict, Any, List, Tuple

from core.logger import get_component_logger
from core.exceptions import PromptInjectionDetectedError


class Sanitizer:
    """
    Sanitizes scraped content to prevent prompt injection attacks.
    Removes/escapes system prompts, role injection patterns, and other exploits.
    """

    INJECTION_PATTERNS = [
        r"<system>",
        r"</system>",
        r"<user>",
        r"</user>",
        r"<assistant>",
        r"</assistant>",
        r"\[INST\]",
        r"\[/INST\]",
        r"<<SYS>>",
        r"<</SYS>>",
        r"### Instruction",
        r"### Response",
        r"Ignore previous instructions",
        r"Ignore all previous instructions",
        r"Disregard the above instructions",
        r"You are now in",
        r"Pretend to be",
        r"Act as if you are",
        r"Roleplay as",
        r"<\|system\|>",
        r"<\|user\|>",
        r"<\|assistant\|>",
        r"<\|prompter\|>",
        r"<\|ip\|>",
    ]

    def __init__(self):
        self.logger = get_component_logger("sanitizer")
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.INJECTION_PATTERNS
        ]

    def sanitize(
        self, content: str, raise_on_detection: bool = False
    ) -> Tuple[str, List[str]]:
        """
        Sanitize content by removing/escaping prompt injection patterns.

        Args:
            content: Content to sanitize
            raise_on_detection: Whether to raise exception on detection

        Returns:
            Tuple of (sanitized_content, list of detected patterns)
        """
        detected = []
        sanitized = content

        for pattern in self._compiled_patterns:
            matches = pattern.findall(sanitized)
            if matches:
                for match in matches:
                    if match not in detected:
                        detected.append(match)

                # Replace with placeholder
                sanitized = pattern.sub("[REDACTED]", sanitized)

        # Also check for common injection techniques
        sanitized = self._sanitize_common_techniques(sanitized, detected)

        if detected and raise_on_detection:
            raise PromptInjectionDetectedError(
                content=content[:100], detected_pattern=", ".join(detected[:3])
            )

        if detected:
            self.logger.warning(
                f"Prompt injection patterns detected and removed: {detected[:3]}"
            )

        return sanitized, detected

    def _sanitize_common_techniques(self, content: str, detected: List[str]) -> str:
        """Sanitize common injection techniques."""
        # Remove code blocks that might contain instructions
        content = re.sub(
            r"```json\s*\{.*?\}```", "[JSON_REDACTED]", content, flags=re.DOTALL
        )

        # Remove base64 encoded content that might contain prompts
        if len(content) > 1000:
            content = re.sub(r"[A-Za-z0-9+/]{50,}={0,2}", "[BASE64_REDACTED]", content)

        # Escape HTML entities that could be used for injection
        content = content.replace("<script", "&lt;script")
        content = content.replace("</script", "&lt;/script")

        return content

    def escape_for_markdown(self, content: str) -> str:
        """
        Escape content for safe inclusion in markdown/LLM prompts.

        Args:
            content: Content to escape

        Returns:
            Escaped content
        """
        # Escape the most common problematic characters
        replacements = {
            "```": "\\```",
            "[[": "\\[\\[",
            "]]": "\\]\\]",
            "##": "\\#\\#",
        }

        escaped = content
        for old, new in replacements.items():
            escaped = escaped.replace(old, new)

        return escaped

    def check_safety(self, content: str) -> Dict[str, Any]:
        """
        Check content for potential safety issues.

        Args:
            content: Content to check

        Returns:
            Dict with safety check results
        """
        detected = []

        for pattern in self._compiled_patterns:
            matches = pattern.findall(content)
            detected.extend(matches)

        # Check for suspicious URLs
        suspicious_urls = re.findall(
            r"https?://[^\s]*\b(eval|exec|alert|prompt)\b[^\s]*", content, re.IGNORECASE
        )

        return {
            "is_safe": len(detected) == 0 and len(suspicious_urls) == 0,
            "detected_patterns": list(set(detected)),
            "suspicious_urls": suspicious_urls,
            "detection_count": len(detected),
        }


# Global sanitizer instance
_sanitizer: Optional[Sanitizer] = None


def get_sanitizer() -> Sanitizer:
    """Get singleton sanitizer instance."""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = Sanitizer()
    return _sanitizer
