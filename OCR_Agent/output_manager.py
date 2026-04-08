"""output_manager.py — Dedicated output directory management.

All extraction results, analyses, and batch reports are saved through this
module into the ``outputs/`` directory.  The output directory is the ONLY
writable location — source files are never modified.

Directory structure (when ``organize_by_type`` is True):
    outputs/
    ├── images/
    ├── documents/
    ├── audio/
    ├── video/
    ├── analysis/        ← vision understanding results
    ├── batch/           ← batch processing summaries
    └── other/
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import OUTPUT_CFG


class OutputManager:
    """Manages all output file writing for the pipeline.

    Files are organised by media type into sub-directories and optionally
    timestamped to prevent overwrites.
    """

    # Sub-directory mapping
    _TYPE_DIRS = {
        "image": "images",
        "document": "documents",
        "audio": "audio",
        "video": "video",
        "spreadsheet": "spreadsheets",
        "presentation": "presentations",
        "code": "code",
        "archive": "archives",
        "analysis": "analysis",
        "batch": "batch",
        "unknown": "other",
    }

    def __init__(self) -> None:
        self._base = Path(OUTPUT_CFG.base_dir).resolve()
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Create the output directory and all sub-directories."""
        self._base.mkdir(parents=True, exist_ok=True)
        if OUTPUT_CFG.organize_by_type:
            for subdir in self._TYPE_DIRS.values():
                (self._base / subdir).mkdir(exist_ok=True)

    def _get_dir(self, category: str) -> Path:
        """Get the appropriate sub-directory for a file category."""
        if OUTPUT_CFG.organize_by_type:
            subdir = self._TYPE_DIRS.get(category, "other")
            return self._base / subdir
        return self._base

    def _timestamped_name(self, basename: str) -> str:
        """Prefix a filename with a timestamp if configured."""
        if OUTPUT_CFG.timestamp_files:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{ts}_{basename}"
        return basename

    # ------------------------------------------------------------------
    # Save Methods
    # ------------------------------------------------------------------

    def save_result(
        self,
        result: dict[str, Any],
        category: str = "unknown",
        custom_name: str | None = None,
    ) -> dict[str, str]:
        """Save an extraction result as JSON and optional text file.

        Args:
            result: The ExtractionResult dict.
            category: Media type category for directory routing.
            custom_name: Override for the base filename.

        Returns:
            Dict with keys 'json_path' and optionally 'text_path'.
        """
        file_name = custom_name or result.get("file_name", "result")
        stem = Path(file_name).stem
        target_dir = self._get_dir(category)
        paths: dict[str, str] = {}

        # JSON output
        if OUTPUT_CFG.save_json:
            json_name = self._timestamped_name(f"{stem}.json")
            json_path = target_dir / json_name
            json_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            paths["json_path"] = str(json_path)

        # Plain text output
        if OUTPUT_CFG.save_text:
            content = result.get("extracted_content", "") or result.get("analysis", "")
            if content:
                txt_name = self._timestamped_name(f"{stem}.txt")
                txt_path = target_dir / txt_name
                txt_path.write_text(content, encoding="utf-8")
                paths["text_path"] = str(txt_path)

        return paths

    def save_analysis(
        self,
        analysis: dict[str, Any],
        custom_name: str | None = None,
    ) -> dict[str, str]:
        """Save a vision analysis result.

        Args:
            analysis: The VisionAnalysis dict.
            custom_name: Override for the base filename.

        Returns:
            Dict with keys 'json_path' and optionally 'text_path'.
        """
        return self.save_result(analysis, category="analysis", custom_name=custom_name)

    def save_batch_report(self, report: dict[str, Any]) -> str:
        """Save a batch processing report.

        Args:
            report: The BatchResult dict.

        Returns:
            Path to the saved JSON report.
        """
        target_dir = self._get_dir("batch")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"batch_report_{ts}.json"
        report_path = target_dir / report_name
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return str(report_path)

    def save_folder_listing(self, listing: dict[str, Any]) -> str:
        """Save a folder listing / browse result.

        Args:
            listing: The FolderListing dict.

        Returns:
            Path to the saved JSON.
        """
        target_dir = self._get_dir("batch")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        listing_name = f"folder_listing_{ts}.json"
        listing_path = target_dir / listing_name
        listing_path.write_text(
            json.dumps(listing, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return str(listing_path)

    def get_output_dir(self) -> str:
        """Return the base output directory path."""
        return str(self._base)

    def list_outputs(self, category: str | None = None) -> list[str]:
        """List all output files, optionally filtered by category.

        Args:
            category: Optional category to filter by.

        Returns:
            List of absolute paths to output files.
        """
        if category:
            target_dir = self._get_dir(category)
            if target_dir.is_dir():
                return sorted(str(f) for f in target_dir.rglob("*") if f.is_file())
            return []

        return sorted(str(f) for f in self._base.rglob("*") if f.is_file())


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

output_mgr = OutputManager()
