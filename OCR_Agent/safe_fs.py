"""safe_fs.py — Read-Only Filesystem Guard for Project Omni-Extract.

This module is the security boundary.  Every file and directory operation
in the entire pipeline MUST go through ``SafeFileSystem``.  It enforces the
strict read-only policy: the agent can browse folders, open files, and
analyze content, but it CANNOT rename, delete, move, or modify any source
file.

The ONLY writable location is the dedicated ``outputs/`` directory.
"""

from __future__ import annotations

import os
import mimetypes
from pathlib import Path
from typing import Any

from config import SECURITY_CFG, OUTPUT_CFG


class PermissionDeniedError(PermissionError):
    """Raised when a blocked filesystem operation is attempted."""

    def __init__(self, operation: str, path: str) -> None:
        self.operation = operation
        self.path = path
        super().__init__(
            f"🚫 BLOCKED: Operation '{operation}' is not permitted on '{path}'. "
            f"The agent has READ-ONLY access to source files. "
            f"Only the outputs directory is writable."
        )


class SafeFileSystem:
    """Read-only filesystem wrapper that enforces security constraints.

    This class is the ONLY sanctioned way to interact with the filesystem.
    It allows:
        ✅ Reading file contents
        ✅ Listing directory contents
        ✅ Getting file metadata (size, extension, etc.)
        ✅ Writing to the outputs/ directory

    It blocks:
        ❌ Renaming files
        ❌ Deleting files
        ❌ Moving files
        ❌ Modifying source files
        ❌ Any destructive operation
    """

    def __init__(self) -> None:
        self._read_only = SECURITY_CFG.read_only
        self._output_dir = Path(OUTPUT_CFG.base_dir).resolve()

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def _assert_read_only(self, operation: str, path: str) -> None:
        """Raise PermissionDeniedError if the operation is blocked."""
        if self._read_only and operation in SECURITY_CFG.blocked_operations:
            raise PermissionDeniedError(operation, path)

    def _is_output_path(self, path: Path) -> bool:
        """Return True if the path is inside the outputs/ directory."""
        try:
            path.resolve().relative_to(self._output_dir)
            return True
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # READ Operations (always allowed)
    # ------------------------------------------------------------------

    def read_file(self, file_path: str, mode: str = "rb") -> bytes | str:
        """Read and return the contents of a file.

        Args:
            file_path: Absolute or relative path to the file.
            mode: Open mode ('rb' for binary, 'r' for text).

        Returns:
            File contents as bytes or string.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(p, mode) as fh:
            return fh.read()

    def read_text(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read a text file and return its contents as a string."""
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return p.read_text(encoding=encoding, errors="replace")

    def read_binary(self, file_path: str) -> bytes:
        """Read a binary file and return its contents as bytes."""
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return p.read_bytes()

    # ------------------------------------------------------------------
    # LIST Operations (always allowed)
    # ------------------------------------------------------------------

    def list_dir(self, dir_path: str) -> list[dict[str, Any]]:
        """List all entries in a directory with metadata.

        Args:
            dir_path: Absolute or relative path to the directory.

        Returns:
            List of dicts with keys: name, path, is_dir, size_bytes,
            extension, category (file type).
        """
        from file_identifier import FileIdentifier

        p = Path(dir_path).resolve()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        identifier = FileIdentifier()
        entries: list[dict[str, Any]] = []

        for item in sorted(p.iterdir()):
            entry: dict[str, Any] = {
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
            }

            if item.is_file():
                stat = item.stat()
                entry["size_bytes"] = stat.st_size
                entry["extension"] = item.suffix.lower()
                info = identifier.identify(str(item))
                entry["category"] = info.get("category", "unknown")
                entry["mime_type"] = info.get("mime_type", "unknown")
            elif item.is_dir():
                # Count children without recursing deeply
                try:
                    entry["child_count"] = sum(1 for _ in item.iterdir())
                except PermissionError:
                    entry["child_count"] = -1

            entries.append(entry)

        return entries

    def list_files_recursive(
        self, dir_path: str, extensions: list[str] | None = None
    ) -> list[str]:
        """Recursively list all files, optionally filtered by extension.

        Args:
            dir_path: Root directory to scan.
            extensions: Optional list of extensions to include (e.g. ['.png', '.jpg']).

        Returns:
            List of absolute file paths.
        """
        p = Path(dir_path).resolve()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        results: list[str] = []
        for item in p.rglob("*"):
            if item.is_file():
                if extensions is None or item.suffix.lower() in extensions:
                    results.append(str(item))
        return sorted(results)

    def tree(self, dir_path: str, max_depth: int = 3, _current_depth: int = 0) -> str:
        """Generate a tree-style string representation of a directory.

        Args:
            dir_path: Root directory.
            max_depth: Maximum depth to recurse.

        Returns:
            A formatted tree string.
        """
        p = Path(dir_path).resolve()
        if not p.is_dir():
            return f"[Not a directory: {dir_path}]"

        lines: list[str] = []
        if _current_depth == 0:
            lines.append(f"📁 {p.name}/")

        if _current_depth >= max_depth:
            lines.append("  " * (_current_depth + 1) + "...")
            return "\n".join(lines)

        try:
            items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            lines.append("  " * (_current_depth + 1) + "[Permission Denied]")
            return "\n".join(lines)

        indent = "  " * (_current_depth + 1)
        for item in items:
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            if item.is_dir():
                lines.append(f"{indent}📁 {item.name}/")
                sub_tree = self.tree(
                    str(item), max_depth, _current_depth + 1
                )
                # Append sub-tree lines (skip the root line which we already added)
                sub_lines = sub_tree.split("\n")
                lines.extend(sub_lines[1:] if sub_lines else [])
            else:
                size = self._human_size(item.stat().st_size)
                lines.append(f"{indent}📄 {item.name}  ({size})")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # STAT Operations (always allowed)
    # ------------------------------------------------------------------

    def stat(self, file_path: str) -> dict[str, Any]:
        """Get file metadata without reading contents.

        Args:
            file_path: Path to the file.

        Returns:
            Dict with: name, path, size_bytes, size_human, extension,
            mime_type, exists, is_file, is_dir.
        """
        p = Path(file_path).resolve()
        result: dict[str, Any] = {
            "name": p.name,
            "path": str(p),
            "exists": p.exists(),
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
        }

        if p.is_file():
            st = p.stat()
            result["size_bytes"] = st.st_size
            result["size_human"] = self._human_size(st.st_size)
            result["extension"] = p.suffix.lower()
            mime, _ = mimetypes.guess_type(str(p))
            result["mime_type"] = mime or "application/octet-stream"

        return result

    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        return Path(path).resolve().exists()

    def is_file(self, path: str) -> bool:
        """Check if a path is a file."""
        return Path(path).resolve().is_file()

    def is_dir(self, path: str) -> bool:
        """Check if a path is a directory."""
        return Path(path).resolve().is_dir()

    # ------------------------------------------------------------------
    # WRITE Operations (ONLY to outputs/ directory)
    # ------------------------------------------------------------------

    def write_output(self, relative_path: str, content: str | bytes) -> str:
        """Write content to the outputs/ directory.

        This is the ONLY write operation permitted.  The path must
        resolve to somewhere inside the configured output directory.

        Args:
            relative_path: Path relative to the output base directory.
            content: Text or binary content to write.

        Returns:
            Absolute path to the written file.

        Raises:
            PermissionDeniedError: If the resolved path is outside outputs/.
        """
        target = (self._output_dir / relative_path).resolve()

        # Double-check the target is inside the output directory
        if not self._is_output_path(target):
            raise PermissionDeniedError(
                "write",
                str(target),
            )

        # Create parent directories
        target.parent.mkdir(parents=True, exist_ok=True)

        mode = "w" if isinstance(content, str) else "wb"
        with open(target, mode, encoding="utf-8" if mode == "w" else None) as fh:
            fh.write(content)

        return str(target)

    # ------------------------------------------------------------------
    # BLOCKED Operations
    # ------------------------------------------------------------------

    def rename(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: Renaming files is not permitted."""
        raise PermissionDeniedError("rename", str(args[0] if args else "unknown"))

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: Deleting files is not permitted."""
        raise PermissionDeniedError("delete", str(args[0] if args else "unknown"))

    def move(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: Moving files is not permitted."""
        raise PermissionDeniedError("move", str(args[0] if args else "unknown"))

    def chmod(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: Changing permissions is not permitted."""
        raise PermissionDeniedError("chmod", str(args[0] if args else "unknown"))

    def copy(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: Copying to source locations is not permitted."""
        raise PermissionDeniedError("copy_to_source", str(args[0] if args else "unknown"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to a human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0  # type: ignore[assignment]
        return f"{size_bytes:.1f} PB"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

safe_fs = SafeFileSystem()
