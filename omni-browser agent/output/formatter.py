"""
Output formatter for Omni Browser Agent.
Formats results as Markdown or JSON for different output types.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from models.schemas import (
    TaskResult,
    ExtractionResult,
    PlatformPost,
    SynthesizedPrompt,
    SessionHistory,
)


class OutputFormatter:
    """Formats output in various formats (Markdown, JSON, etc.)."""

    @staticmethod
    def format_task_result(result: TaskResult, format: str = "markdown") -> str:
        """Format task result."""
        if format == "json":
            return json.dumps(result.model_dump(), indent=2, default=str)

        # Markdown format
        lines = [
            f"# Task Result: {result.task_id}",
            "",
            f"**Status:** {result.status.value}",
            f"**Start Time:** {result.start_time.isoformat()}",
        ]

        if result.end_time:
            duration = (result.end_time - result.start_time).total_seconds()
            lines.append(f"**Duration:** {duration:.2f} seconds")

        if result.error:
            lines.append(f"**Error:** {result.error}")

        if result.output:
            lines.append("")
            lines.append("## Output")
            lines.append("```json")
            lines.append(json.dumps(result.output, indent=2, default=str))
            lines.append("```")

        return "\n".join(lines)

    @staticmethod
    def format_extraction_result(
        result: ExtractionResult, format: str = "markdown"
    ) -> str:
        """Format extraction result."""
        if format == "json":
            return json.dumps(result.model_dump(), indent=2, default=str)

        lines = [
            f"# Extraction Result: {result.platform.value}",
            "",
            f"**Success:** {result.success}",
            f"**Timestamp:** {result.timestamp.isoformat()}",
        ]

        if result.posts:
            lines.append("")
            lines.append("## Extracted Content")

            for post in result.posts:
                lines.append(OutputFormatter._format_post(post))

        if result.error:
            lines.append(f"**Error:** {result.error}")

        return "\n".join(lines)

    @staticmethod
    def _format_post(post: PlatformPost) -> str:
        """Format a platform post."""
        lines = [
            f"### {post.platform.value.title()} Post: {post.post_id}",
            "",
            f"**Author:** {post.author}",
            f"**URL:** {post.url}",
            f"**Timestamp:** {post.timestamp.isoformat()}",
            "",
            "**Content:**",
            post.content,
            "",
            f"**Engagement:** {post.likes} likes, {post.comments} comments, {post.shares} shares",
        ]

        if post.media_urls:
            lines.append("")
            lines.append("**Media:**")
            for url in post.media_urls:
                lines.append(f"- {url}")

        return "\n".join(lines)

    @staticmethod
    def format_synthesized_prompt(
        result: SynthesizedPrompt, format: str = "markdown"
    ) -> str:
        """Format synthesized prompt result."""
        if format == "json":
            return json.dumps(result.model_dump(), indent=2, default=str)

        lines = [
            "# Synthesized Prompt",
            "",
            "## Original Prompts",
            "",
            f"**Prompt A:** {result.original_prompt_a}",
            "",
            f"**Prompt B:** {result.original_prompt_b}",
            "",
            "## Synthesized Result",
            "",
            f"**Synthesized Prompt:** {result.synthesized_prompt}",
            "",
            f"**Explanation:** {result.explanation}",
            "",
            f"**Confidence:** {result.confidence:.2f}",
        ]

        if result.dropped_constraints:
            lines.append("")
            lines.append("**Dropped Constraints:**")
            for constraint in result.dropped_constraints:
                lines.append(f"- {constraint}")

        return "\n".join(lines)

    @staticmethod
    def format_session_history(
        history: List[SessionHistory], format: str = "markdown"
    ) -> str:
        """Format session history."""
        if format == "json":
            return json.dumps([h.model_dump() for h in history], indent=2, default=str)

        lines = ["# Session History", ""]

        for entry in history:
            lines.append(f"## {entry.id}")
            lines.append(f"**Timestamp:** {entry.timestamp.isoformat()}")
            lines.append(f"**Task:** {entry.task.description}")
            lines.append(f"**Status:** {entry.result.status.value}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_search_results(results: List[Dict[str, Any]]) -> str:
        """Format web search results."""
        if not results:
            return "No results found."

        lines = ["# Search Results", ""]

        for i, result in enumerate(results, 1):
            lines.append(f"## {i}. {result.get('title', 'Untitled')}")
            lines.append(f"**URL:** {result.get('url', 'N/A')}")
            lines.append("")
            if result.get("snippet"):
                lines.append(result["snippet"])
            lines.append("")

        return "\n".join(lines)
