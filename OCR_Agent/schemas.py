"""schemas.py — Pydantic output models for Project Omni-Extract.

Every tool / task that emits results MUST serialise into these models so the
upstream Super Agent always receives a predictable, machine-readable JSON
envelope.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =========================================================================
# Media / File Type Enums
# =========================================================================

class MediaType(str, Enum):
    """Supported media categories recognised by the extraction pipeline."""

    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    CODE = "code"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


# =========================================================================
# Core Extraction Result
# =========================================================================

class ExtractionResult(BaseModel):
    """Canonical output contract between the Omni-OCR Sub-Agent and any
    upstream Super Agent.

    Attributes:
        file_name: Original file name (basename, no directory).
        media_type: Detected category of the ingested file.
        extraction_method: The NVIDIA model / tool that performed extraction.
        extracted_content: Raw OCR text, transcript, or video-derived text.
        confidence_score: Heuristic confidence in the extraction (0.0–1.0).
        error_log: Human-readable error details when a tool fails gracefully.
    """

    file_name: str = Field(
        ...,
        description="Original file name (basename only).",
    )
    media_type: str = Field(
        ...,
        description="One of: audio, video, image, document, spreadsheet, "
                    "presentation, code, archive, unknown.",
    )
    extraction_method: str = Field(
        ...,
        description="NVIDIA model identifier used for extraction.",
    )
    extracted_content: str = Field(
        default="",
        description="The raw OCR text, transcript, or video text.",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Heuristic confidence score between 0.0 and 1.0.",
    )
    error_log: Optional[str] = Field(
        default=None,
        description="Details if a tool failed gracefully.",
    )


# =========================================================================
# File Identification Result
# =========================================================================

class FileInfo(BaseModel):
    """Rich metadata about a single file."""

    file_name: str = Field(..., description="Basename of the file.")
    file_path: str = Field(..., description="Absolute path to the file.")
    extension: str = Field(default="", description="File extension (lowercase, with dot).")
    category: str = Field(default="unknown", description="File category.")
    mime_type: str = Field(default="application/octet-stream", description="MIME type.")
    size_bytes: int = Field(default=0, description="File size in bytes.")
    size_human: str = Field(default="0 B", description="Human-readable file size.")
    is_supported: bool = Field(
        default=False,
        description="Whether this file type is supported by the extraction pipeline.",
    )


# =========================================================================
# Vision / Image Understanding Result
# =========================================================================

class VisionAnalysis(BaseModel):
    """Output from the image understanding / scene analysis tool."""

    file_name: str = Field(..., description="Name of the analyzed image file.")
    analysis: str = Field(default="", description="Full analysis text from the vision model.")
    extracted_text: str = Field(
        default="",
        description="Any text detected verbatim in the image.",
    )
    model_used: str = Field(default="", description="Vision model identifier.")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    error_log: Optional[str] = Field(default=None)


# =========================================================================
# Batch Processing Result
# =========================================================================

class BatchFileResult(BaseModel):
    """Result for a single file within a batch run."""

    file_name: str
    file_path: str
    category: str
    status: str = Field(description="One of: success, error, skipped.")
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class BatchResult(BaseModel):
    """Summary of a batch processing run across a folder."""

    directory: str = Field(..., description="Directory that was processed.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of the batch run.",
    )
    total_files: int = Field(default=0)
    processed: int = Field(default=0)
    succeeded: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)
    by_category: dict[str, int] = Field(default_factory=dict)
    files: list[BatchFileResult] = Field(default_factory=list)


# =========================================================================
# Folder Browse Result
# =========================================================================

class FolderEntry(BaseModel):
    """Single entry in a folder listing."""

    name: str
    path: str
    is_dir: bool
    size_bytes: Optional[int] = None
    size_human: Optional[str] = None
    extension: Optional[str] = None
    category: Optional[str] = None
    mime_type: Optional[str] = None
    child_count: Optional[int] = None


class FolderListing(BaseModel):
    """Full listing of a directory."""

    directory: str
    total_entries: int
    directories: int = 0
    files: int = 0
    entries: list[FolderEntry] = Field(default_factory=list)
