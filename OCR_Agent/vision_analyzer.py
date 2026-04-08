"""vision_analyzer.py — Image understanding beyond OCR.

While VisionOCRTool extracts text, this module provides deep image
understanding: scene description, object listing, color analysis,
layout analysis, and contextual interpretation.

Uses the same NVIDIA vision model but with a specialised
``understanding_prompt`` configured in ``config.yaml``.
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import API, MODELS, VISION_CFG
from schemas import VisionAnalysis
from tools import _get_api_key, _encode_image_to_data_uri


# =========================================================================
# CrewAI Tool — Vision Understanding
# =========================================================================

class VisionUnderstandingInput(BaseModel):
    """Input schema for VisionUnderstandingTool."""
    file_path: str = Field(
        ..., description="Absolute path to an image file to analyze."
    )


class VisionUnderstandingTool(BaseTool):
    """Analyze and understand the contents of an image.

    Goes beyond OCR to provide scene descriptions, object detection,
    color analysis, layout interpretation, and contextual understanding.
    """

    name: str = "vision_understanding_tool"
    description: str = (
        "Analyzes an image to understand its contents. Provides detailed "
        "scene descriptions, identifies objects and elements, extracts text, "
        "describes colors and style, analyzes layout, and interprets context. "
        "Use this when you need to UNDERSTAND what's in an image, not just "
        "extract its text. Input: absolute file path to an image."
    )
    args_schema: Type[BaseModel] = VisionUnderstandingInput

    def _run(self, file_path: str) -> str:
        """Execute vision understanding analysis.

        Args:
            file_path: Absolute path to the image.

        Returns:
            Comprehensive analysis text on success, or error string.
        """
        try:
            api_key = _get_api_key()
            data_uri = _encode_image_to_data_uri(file_path)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            payload = {
                "model": MODELS.vision,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": VISION_CFG.understanding_prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": data_uri},
                            },
                        ],
                    }
                ],
                "max_tokens": VISION_CFG.max_tokens,
                "temperature": VISION_CFG.temperature,
                "stream": False,
            }

            import time
            from requests.exceptions import RequestException
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"{API.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=VISION_CFG.timeout_seconds,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                except RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(2 ** attempt)  # Exponential backoff

        except Exception as exc:
            return (
                f"[TOOL_ERROR] VisionUnderstandingTool failed: {exc}\n"
                f"{traceback.format_exc()}"
            )


# =========================================================================
# High-Level Analyze Function
# =========================================================================

def analyze_image(file_path: str) -> dict:
    """Analyze an image and return a structured VisionAnalysis result.

    Args:
        file_path: Path to the image file.

    Returns:
        VisionAnalysis dict with analysis text, extracted text, model info.
    """
    file_name = Path(file_path).name
    tool = VisionUnderstandingTool()
    raw_output = tool._run(file_path=file_path)

    if raw_output.startswith("[TOOL_ERROR]"):
        return VisionAnalysis(
            file_name=file_name,
            analysis="",
            extracted_text="",
            model_used=MODELS.vision,
            confidence_score=0.0,
            error_log=raw_output,
        ).model_dump()

    return VisionAnalysis(
        file_name=file_name,
        analysis=raw_output,
        extracted_text="",  # Understanding mode focuses on analysis
        model_used=MODELS.vision,
        confidence_score=0.85,
        error_log=None,
    ).model_dump()
