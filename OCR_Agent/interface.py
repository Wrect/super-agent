"""interface.py — Public integration wrapper for the Omni-OCR Sub-Agent.

The Super Agent imports ``OmniOCREngine`` from this module and calls its
``extract_media``, ``understand_image``, or ``process_batch`` methods.
All extraction logic is encapsulated here.

This module calls NVIDIA tools directly for maximum reliability, then
packages results into schema-compliant dicts.  All outputs are automatically
saved to the dedicated ``outputs/`` directory.

Security: ALL source file access is READ-ONLY.  No files are ever renamed,
deleted, moved, or modified.

Example usage from a Super Agent::

    from interface import OmniOCREngine

    engine = OmniOCREngine()
    result: dict = engine.extract_media("/data/invoice.pdf")
    analysis: dict = engine.understand_image("/data/photo.jpg")
    batch: dict = engine.process_batch("/data/scans/")
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import Any

from config import API, MODELS, AGENT_CFG
from schemas import ExtractionResult
from tools import (
    VisionOCRTool,
    AudioTranscriptionTool,
    VideoExtractionTool,
    detect_media_type,
)
from output_manager import output_mgr
from file_identifier import identify_file


class OmniOCREngine:
    """High-level integration facade for the Omni-OCR extraction pipeline.

    This class is the **only** public interface the Super Agent needs.
    It invokes the correct NVIDIA tool directly based on file type, then
    packages the result into the guaranteed ``ExtractionResult`` schema.

    All operations are READ-ONLY on source files.  Outputs are saved
    automatically to the ``outputs/`` directory.

    Attributes:
        api_ready: Whether the NVIDIA API key is available.
    """

    # Tool instances — created once, reused across calls
    _vision_tool = VisionOCRTool()
    _audio_tool = AudioTranscriptionTool()
    _video_tool = VideoExtractionTool()

    # Media type → (tool, model name) mapping
    _TOOL_MAP: dict[str, tuple] = {
        "image":    (_vision_tool, MODELS.vision),
        "document": (_vision_tool, MODELS.vision),
        "audio":    (_audio_tool,  MODELS.audio_asr),
        "video":    (_video_tool,  MODELS.vision),
    }

    def __init__(self) -> None:
        """Initialise the engine.

        ``config.py`` loads ``.env`` on import, so the API key is already
        available via ``config.API``.
        """
        self.api_ready: bool = API.validate()

    # ------------------------------------------------------------------
    # Public API — Extract
    # ------------------------------------------------------------------

    def extract_media(self, file_path: str) -> dict[str, Any]:
        """Run the Omni-OCR extraction pipeline on a single file.

        This is the **primary entry-point** that Super Agents should call.

        Args:
            file_path: Absolute path to the file to process.

        Returns:
            A dictionary matching the ``ExtractionResult`` Pydantic schema.
            On catastrophic failure the dict will still be schema-compliant
            with ``error_log`` populated and ``confidence_score`` at 0.0.

        Raises:
            Nothing — all exceptions are caught and returned inside the
            ``error_log`` field.
        """
        file_path = str(Path(file_path).resolve())
        file_name = Path(file_path).name

        # Pre-flight checks
        if not os.path.isfile(file_path):
            return self._error_result(
                file_name=file_name,
                error=f"File not found: {file_path}",
            )

        if not self.api_ready:
            return self._error_result(
                file_name=file_name,
                error="NVIDIA_API_KEY is not set in the environment.",
            )

        # Detect media type and select tool
        media_type = detect_media_type(file_path)

        if media_type not in self._TOOL_MAP:
            # Identify the file for better error reporting
            info = identify_file(file_path)
            return self._error_result(
                file_name=file_name,
                error=(
                    f"Unsupported file type for extraction: "
                    f"{info['category']} ({Path(file_path).suffix}). "
                    f"Supported: image, document, audio, video."
                ),
            )

        tool, model_name = self._TOOL_MAP[media_type]

        try:
            # Call the NVIDIA tool directly — READ-ONLY on the source file
            raw_output: str = tool._run(file_path=file_path)

            # Check for tool-level errors
            if raw_output.startswith("[TOOL_ERROR]"):
                result = ExtractionResult(
                    file_name=file_name,
                    media_type=media_type,
                    extraction_method=model_name,
                    extracted_content="",
                    confidence_score=0.0,
                    error_log=raw_output,
                ).model_dump()
            else:
                # Success — package the extracted content
                result = ExtractionResult(
                    file_name=file_name,
                    media_type=media_type,
                    extraction_method=model_name,
                    extracted_content=raw_output,
                    confidence_score=AGENT_CFG.default_confidence,
                    error_log=None,
                ).model_dump()

            # Auto-save to outputs/
            output_mgr.save_result(result, category=media_type)
            return result

        except Exception as exc:
            return self._error_result(
                file_name=file_name,
                error=f"Pipeline exception: {exc}\n{traceback.format_exc()}",
            )

    # ------------------------------------------------------------------
    # Public API — Understand (Vision)
    # ------------------------------------------------------------------

    def understand_image(self, file_path: str) -> dict[str, Any]:
        """Analyze and understand an image using vision AI.

        Goes beyond OCR to provide scene descriptions, object detection,
        color analysis, and contextual interpretation.

        Args:
            file_path: Absolute path to the image file.

        Returns:
            A VisionAnalysis dict.
        """
        from vision_analyzer import analyze_image

        file_path = str(Path(file_path).resolve())

        if not os.path.isfile(file_path):
            return {
                "file_name": Path(file_path).name,
                "analysis": "",
                "extracted_text": "",
                "model_used": MODELS.vision,
                "confidence_score": 0.0,
                "error_log": f"File not found: {file_path}",
            }

        # Verify it's an image
        info = identify_file(file_path)
        if info["category"] != "image":
            return {
                "file_name": Path(file_path).name,
                "analysis": "",
                "extracted_text": "",
                "model_used": MODELS.vision,
                "confidence_score": 0.0,
                "error_log": (
                    f"Vision understanding requires an image file. "
                    f"Got: {info['category']} ({info['extension']})"
                ),
            }

        result = analyze_image(file_path)

        # Auto-save to outputs/analysis/
        output_mgr.save_analysis(result)
        return result

    # ------------------------------------------------------------------
    # Public API — Batch
    # ------------------------------------------------------------------

    def process_batch(
        self,
        dir_path: str,
        recursive: bool = False,
        progress_callback=None,
    ) -> dict[str, Any]:
        """Process all supported files in a directory.

        Args:
            dir_path: Path to the directory.
            recursive: Whether to scan subdirectories.
            progress_callback: Optional callback(current, total, filename).

        Returns:
            BatchResult dict with per-file results and aggregate stats.
        """
        from batch_processor import batch_processor

        return batch_processor.process_folder(
            dir_path,
            extract_fn=self.extract_media,
            recursive=recursive,
            progress_callback=progress_callback,
        )

    # ------------------------------------------------------------------
    # Public API — Identify
    # ------------------------------------------------------------------

    def identify(self, path: str) -> dict[str, Any]:
        """Identify a file or folder's contents.

        Args:
            path: Path to a file or directory.

        Returns:
            FileInfo dict (for files) or folder identification summary (for dirs).
        """
        from file_identifier import identify_file, identify_folder

        p = Path(path).resolve()
        if p.is_dir():
            return identify_folder(str(p))
        elif p.is_file():
            return identify_file(str(p))
        else:
            return {"error": f"Path not found: {path}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error_result(file_name: str, error: str) -> dict[str, Any]:
        """Build a minimal, schema-compliant error result.

        Args:
            file_name: Name of the file that was being processed.
            error: Human-readable error description.

        Returns:
            A dict matching ``ExtractionResult`` with ``error_log`` set.
        """
        return ExtractionResult(
            file_name=file_name,
            media_type="unknown",
            extraction_method="none",
            extracted_content="",
            confidence_score=0.0,
            error_log=error,
        ).model_dump()


# ---------------------------------------------------------------------------
# Optional CLI entry-point (for testing only)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python interface.py <file_path>")
        sys.exit(1)

    engine = OmniOCREngine()
    output = engine.extract_media(sys.argv[1])
    print(json.dumps(output, indent=2, ensure_ascii=False))
