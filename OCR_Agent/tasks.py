"""tasks.py — CrewAI Task definitions for Project Omni-Extract.

Each task is parameterised by a ``file_path`` at runtime and bound to the
``OmniExtractor`` agent. The ``output_pydantic`` parameter guarantees that
CrewAI validates the final answer against :class:`schemas.ExtractionResult`.
"""

from __future__ import annotations

from pathlib import Path

from crewai import Agent, Task

from config import AGENT_CFG
from schemas import ExtractionResult
from tools import detect_media_type


def build_extraction_task(agent: Agent, file_path: str) -> Task:
    """Build the extraction task for a given file.

    Args:
        agent: The ``OmniExtractor`` agent that will execute this task.
        file_path: Absolute path to the file to be processed.

    Returns:
        A ``Task`` whose output is validated against ``ExtractionResult``.
    """
    file_name = Path(file_path).name
    media_type = detect_media_type(file_path)
    confidence = AGENT_CFG.default_confidence

    description = (
        f"Process the following file and extract all textual content from it.\n\n"
        f"**File Path:** `{file_path}`\n"
        f"**File Name:** `{file_name}`\n"
        f"**Detected Media Type:** `{media_type}`\n\n"
        f"Instructions:\n"
        f"1. Based on the media type, select the appropriate extraction tool:\n"
        f"   - image / document → `vision_ocr_tool`\n"
        f"   - audio → `audio_transcription_tool`\n"
        f"   - video → `video_extraction_tool`\n"
        f"2. Invoke the tool with the file path: `{file_path}`\n"
        f"3. Collect the raw extracted text from the tool output.\n"
        f"4. If the tool returns an error (starts with [TOOL_ERROR]), record it "
        f"   in the `error_log` field and set `confidence_score` to 0.0.\n"
        f"5. Otherwise, set `confidence_score` to {confidence} (default heuristic).\n"
        f"6. Return the result formatted EXACTLY as the ExtractionResult schema:\n"
        f'   - file_name: "{file_name}"\n'
        f'   - media_type: "{media_type}"\n'
        f"   - extraction_method: (the NVIDIA model you used)\n"
        f"   - extracted_content: (the raw text)\n"
        f"   - confidence_score: (float)\n"
        f"   - error_log: (null or error string)\n"
    )

    expected_output = (
        "A JSON object matching the ExtractionResult schema with fields: "
        "file_name, media_type, extraction_method, extracted_content, "
        "confidence_score, and error_log."
    )

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
        output_pydantic=ExtractionResult,
    )
