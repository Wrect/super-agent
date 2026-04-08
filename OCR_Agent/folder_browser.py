"""folder_browser.py — Read-only folder navigation for Project Omni-Extract.

Allows the agent to browse directories, list files with rich metadata,
and navigate into sub-folders — all with STRICT read-only access.
No files can be renamed, deleted, moved, or modified.

Uses ``safe_fs.py`` as the security boundary for all I/O operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from safe_fs import safe_fs
from file_identifier import FileIdentifier
from schemas import FolderEntry, FolderListing


class FolderBrowser:
    """Interactive read-only folder navigator.

    Provides methods to:
        ✅ List contents of any accessible directory
        ✅ Navigate into sub-directories
        ✅ Get file metadata and type identification
        ✅ Generate directory tree views
        ✅ Search for files by name or type

    Security:
        ❌ Cannot rename, delete, move, or modify any file
        ❌ Cannot write outside the outputs/ directory
    """

    def __init__(self) -> None:
        self._identifier = FileIdentifier()
        self._current_dir: Path | None = None

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def browse(self, dir_path: str) -> dict[str, Any]:
        """List all entries in a directory with rich metadata.

        Args:
            dir_path: Absolute or relative path to browse.

        Returns:
            FolderListing dict with directory info and entries.
        """
        p = Path(dir_path).resolve()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        self._current_dir = p
        entries: list[dict[str, Any]] = []
        dir_count = 0
        file_count = 0

        try:
            items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return FolderListing(
                directory=str(p),
                total_entries=0,
                directories=0,
                files=0,
                entries=[],
            ).model_dump()

        for item in items:
            entry = FolderEntry(
                name=item.name,
                path=str(item),
                is_dir=item.is_dir(),
            )

            if item.is_dir():
                dir_count += 1
                try:
                    entry.child_count = sum(1 for _ in item.iterdir())
                except PermissionError:
                    entry.child_count = -1
            elif item.is_file():
                file_count += 1
                info = self._identifier.identify(str(item))
                entry.size_bytes = info["size_bytes"]
                entry.size_human = info["size_human"]
                entry.extension = info["extension"]
                entry.category = info["category"]
                entry.mime_type = info["mime_type"]

            entries.append(entry)

        listing = FolderListing(
            directory=str(p),
            total_entries=len(entries),
            directories=dir_count,
            files=file_count,
            entries=entries,
        )
        return listing.model_dump()

    def enter(self, subdir_name: str) -> dict[str, Any]:
        """Navigate into a sub-directory from the current location.

        Args:
            subdir_name: Name of the sub-directory to enter.

        Returns:
            FolderListing dict of the entered directory.

        Raises:
            NotADirectoryError: If the target is not a directory.
        """
        if self._current_dir is None:
            raise RuntimeError("No current directory. Call browse() first.")

        target = self._current_dir / subdir_name
        if not target.is_dir():
            raise NotADirectoryError(
                f"'{subdir_name}' is not a directory inside '{self._current_dir}'"
            )

        return self.browse(str(target))

    def go_up(self) -> dict[str, Any]:
        """Navigate to the parent directory.

        Returns:
            FolderListing dict of the parent directory.
        """
        if self._current_dir is None:
            raise RuntimeError("No current directory. Call browse() first.")

        parent = self._current_dir.parent
        return self.browse(str(parent))

    def get_current_dir(self) -> str | None:
        """Return the current directory path, or None if not browsing."""
        return str(self._current_dir) if self._current_dir else None

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_files(
        self,
        dir_path: str,
        name_pattern: str | None = None,
        category: str | None = None,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        """Search for files matching criteria.

        Args:
            dir_path: Root directory to search.
            name_pattern: Substring to match in filenames (case-insensitive).
            category: File category to filter by (e.g. 'image', 'document').
            recursive: Whether to search subdirectories.

        Returns:
            List of FileInfo dicts matching the criteria.
        """
        p = Path(dir_path).resolve()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        results: list[dict[str, Any]] = []
        pattern_iter = p.rglob("*") if recursive else p.iterdir()

        for item in sorted(pattern_iter):
            if not item.is_file():
                continue

            # Name filter
            if name_pattern and name_pattern.lower() not in item.name.lower():
                continue

            info = self._identifier.identify(str(item))

            # Category filter
            if category and info["category"] != category:
                continue

            results.append(info)

        return results

    # ------------------------------------------------------------------
    # Tree View
    # ------------------------------------------------------------------

    def tree(self, dir_path: str, max_depth: int = 3) -> str:
        """Generate a visual tree representation of a directory.

        Args:
            dir_path: Root directory.
            max_depth: Maximum depth to display.

        Returns:
            Formatted tree string.
        """
        return safe_fs.tree(dir_path, max_depth=max_depth)

    # ------------------------------------------------------------------
    # File Info (read-only)
    # ------------------------------------------------------------------

    def inspect_file(self, file_path: str) -> dict[str, Any]:
        """Get detailed metadata about a single file (read-only).

        Args:
            file_path: Path to the file.

        Returns:
            Rich FileInfo dict with category, MIME type, size, etc.
        """
        return self._identifier.identify(file_path)

    def preview_text_file(self, file_path: str, max_lines: int = 50) -> str:
        """Preview the first N lines of a text file (read-only).

        Args:
            file_path: Path to the text file.
            max_lines: Maximum number of lines to return.

        Returns:
            First N lines of the file as a string.
        """
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        info = self._identifier.identify(str(p))
        text_categories = {"document", "code", "unknown"}

        if info["category"] not in text_categories:
            return f"[Cannot preview binary file of type '{info['category']}']"

        try:
            content = safe_fs.read_text(str(p))
            lines = content.splitlines()[:max_lines]
            if len(content.splitlines()) > max_lines:
                lines.append(f"\n... ({len(content.splitlines()) - max_lines} more lines)")
            return "\n".join(lines)
        except UnicodeDecodeError:
            return "[Cannot preview: file contains binary data]"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

folder_browser = FolderBrowser()
