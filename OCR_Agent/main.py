"""main.py — Unified CLI entry point for the Omni-OCR Agent.

Usage:
    python main.py                          → Interactive natural language mode
    python main.py extract <file>           → Single file extraction
    python main.py understand <image>       → Image understanding / analysis
    python main.py batch <folder>           → Batch process a folder
    python main.py identify <file|folder>   → File type identification
    python main.py browse <folder>          → Browse folder contents
    python main.py tree <folder>            → Show directory tree

All operations are READ-ONLY on source files.
Outputs are saved to the dedicated outputs/ directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    """Main entry point."""

    # No args → interactive mode
    if len(sys.argv) < 2:
        _run_interactive()
        return

    command = sys.argv[1].lower()
    target = sys.argv[2] if len(sys.argv) > 2 else None

    if command in ("interactive", "repl", "shell"):
        _run_interactive()

    elif command == "extract":
        if not target:
            print("Usage: python main.py extract <file_path>")
            sys.exit(1)
        _run_extract(target)

    elif command in ("understand", "analyze", "vision"):
        if not target:
            print("Usage: python main.py understand <image_path>")
            sys.exit(1)
        _run_understand(target)

    elif command == "batch":
        if not target:
            print("Usage: python main.py batch <folder_path>")
            sys.exit(1)
        recursive = "--recursive" in sys.argv or "-r" in sys.argv
        _run_batch(target, recursive=recursive)

    elif command == "identify":
        if not target:
            print("Usage: python main.py identify <file_or_folder>")
            sys.exit(1)
        _run_identify(target)

    elif command in ("browse", "ls", "list"):
        _run_browse(target or ".")

    elif command == "tree":
        _run_tree(target or ".")

    elif command == "help":
        _print_help()

    else:
        print(f"Unknown command: {command}")
        print("Run 'python main.py help' for available commands.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Command Implementations
# ---------------------------------------------------------------------------

def _run_interactive() -> None:
    """Start the interactive REPL."""
    from nl_interface import NLInterface
    nl = NLInterface()
    nl.run_interactive()


def _run_extract(file_path: str) -> None:
    """Extract text from a single file."""
    from interface import OmniOCREngine

    engine = OmniOCREngine()
    result = engine.extract_media(file_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _run_understand(file_path: str) -> None:
    """Analyze an image."""
    from interface import OmniOCREngine

    engine = OmniOCREngine()
    result = engine.understand_image(file_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _run_batch(dir_path: str, recursive: bool = False) -> None:
    """Batch process a folder."""
    from interface import OmniOCREngine

    engine = OmniOCREngine()

    def progress(current: int, total: int, filename: str) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r  [{bar}] {current}/{total} ({pct}%) — {filename}", end="", flush=True)

    result = engine.process_batch(dir_path, recursive=recursive, progress_callback=progress)
    print()  # Newline after progress bar
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def _run_identify(path: str) -> None:
    """Identify file or folder types."""
    from interface import OmniOCREngine

    engine = OmniOCREngine()
    result = engine.identify(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _run_browse(dir_path: str) -> None:
    """Browse folder contents."""
    from folder_browser import folder_browser

    result = folder_browser.browse(dir_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _run_tree(dir_path: str) -> None:
    """Show directory tree."""
    from folder_browser import folder_browser

    tree_str = folder_browser.tree(dir_path)
    print(tree_str)


def _print_help() -> None:
    """Print help text."""
    print("""
Omni-OCR Agent — Intelligent File Extraction
=============================================

Usage:
    python main.py                              Interactive mode (REPL)
    python main.py extract <file>               Extract text from a file
    python main.py understand <image>           Analyze an image (vision AI)
    python main.py batch <folder> [-r]          Process all files in a folder
    python main.py identify <file|folder>       Detect file type(s)
    python main.py browse <folder>              List folder contents
    python main.py tree <folder>                Directory tree view
    python main.py help                         Show this message

Options:
    -r, --recursive                             Scan sub-directories (batch mode)

Security:
    🔒 ALL operations are READ-ONLY on your files
    📁 Outputs saved to: ./outputs/
""")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
