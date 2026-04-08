"""file_identifier.py — Rich file-type identification for Project Omni-Extract.

Detects file categories (image, document, spreadsheet, presentation, audio,
video, code, archive) using extension mapping from ``config.yaml`` plus
``mimetypes`` for MIME detection.

Returns rich ``FileInfo`` dicts with name, size, category, MIME type, and
whether the file is supported by the extraction pipeline.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from config import EXTENSION_MAP


# Categories that the extraction pipeline can actually process
_EXTRACTABLE_CATEGORIES = {"image", "document", "audio", "video"}


class FileIdentifier:
    """Identify file types and produce rich metadata.

    Uses the extension → category map from ``config.yaml`` and
    Python's ``mimetypes`` module for MIME detection.
    """

    def __init__(self) -> None:
        self._ext_map = EXTENSION_MAP

    def identify(self, file_path: str) -> dict[str, Any]:
        """Identify a single file and return rich metadata.

        Args:
            file_path: Absolute or relative path to the file.

        Returns:
            A dict with keys: file_name, file_path, extension, category,
            mime_type, size_bytes, size_human, is_supported.
        """
        p = Path(file_path).resolve()

        if not p.is_file():
            return {
                "file_name": p.name,
                "file_path": str(p),
                "extension": p.suffix.lower(),
                "category": "not_found",
                "mime_type": "unknown",
                "size_bytes": 0,
                "size_human": "0 B",
                "is_supported": False,
            }

        ext = p.suffix.lower()
        category = self._ext_map.get(ext, "unknown")
        mime, _ = mimetypes.guess_type(str(p))
        size_bytes = p.stat().st_size

        return {
            "file_name": p.name,
            "file_path": str(p),
            "extension": ext,
            "category": category,
            "mime_type": mime or "application/octet-stream",
            "size_bytes": size_bytes,
            "size_human": self._human_size(size_bytes),
            "is_supported": category in _EXTRACTABLE_CATEGORIES,
        }

    def identify_folder(self, dir_path: str, recursive: bool = False) -> dict[str, Any]:
        """Identify all files in a directory and return a summary.

        Args:
            dir_path: Path to the directory.
            recursive: Whether to scan subdirectories.

        Returns:
            A dict with keys: directory, total_files, by_category (dict),
            supported_count, unsupported_count, files (list of FileInfo dicts).
        """
        p = Path(dir_path).resolve()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        files: list[dict[str, Any]] = []
        by_category: dict[str, int] = {}

        pattern_iter = p.rglob("*") if recursive else p.iterdir()

        for item in sorted(pattern_iter):
            if item.is_file():
                info = self.identify(str(item))
                files.append(info)
                cat = info["category"]
                by_category[cat] = by_category.get(cat, 0) + 1

        supported = sum(1 for f in files if f["is_supported"])

        return {
            "directory": str(p),
            "total_files": len(files),
            "by_category": by_category,
            "supported_count": supported,
            "unsupported_count": len(files) - supported,
            "files": files,
        }

    def get_category(self, file_path: str) -> str:
        """Quick category lookup for a file path.

        Args:
            file_path: Path to the file.

        Returns:
            Category string (e.g. 'image', 'document', 'unknown').
        """
        ext = Path(file_path).suffix.lower()
        return self._ext_map.get(ext, "unknown")

    def is_supported(self, file_path: str) -> bool:
        """Check if a file type is supported by the extraction pipeline."""
        return self.get_category(file_path) in _EXTRACTABLE_CATEGORIES

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to a human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0  # type: ignore[assignment]
        return f"{size_bytes:.1f} PB"


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_identifier = FileIdentifier()


def identify_file(file_path: str) -> dict[str, Any]:
    """Module-level shortcut for ``FileIdentifier.identify``."""
    return _identifier.identify(file_path)


def identify_folder(dir_path: str, recursive: bool = False) -> dict[str, Any]:
    """Module-level shortcut for ``FileIdentifier.identify_folder``."""
    return _identifier.identify_folder(dir_path, recursive=recursive)


def get_category(file_path: str) -> str:
    """Module-level shortcut for ``FileIdentifier.get_category``."""
    return _identifier.get_category(file_path)
