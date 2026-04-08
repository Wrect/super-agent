"""nl_interface.py — Natural Language Command Interface.

Parses human-readable commands into pipeline actions.  Supports commands
like:
    "Extract text from invoice.pdf"
    "What's in this image?"
    "Process all files in /data/scans"
    "Identify the file type of report.xlsx"
    "Browse the /data folder"
    "Show me a tree of my project"
    "help"

All operations are READ-ONLY on source files.  Outputs go to ``outputs/``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    # Graceful fallback if colorama is not installed
    class _NoColor:
        def __getattr__(self, _: str) -> str:
            return ""
    Fore = _NoColor()  # type: ignore[assignment]
    Style = _NoColor()  # type: ignore[assignment]


# =========================================================================
# Intent Definitions
# =========================================================================

class Intent:
    """Known user intents."""

    EXTRACT = "extract"
    UNDERSTAND = "understand"
    BATCH = "batch"
    IDENTIFY = "identify"
    BROWSE = "browse"
    TREE = "tree"
    SEARCH = "search"
    HELP = "help"
    CONFIG = "config"
    OUTPUTS = "outputs"
    QUIT = "quit"
    UNKNOWN = "unknown"


# Intent patterns (compiled once)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Extract
    (Intent.EXTRACT, re.compile(
        r"(?:extract|ocr|read|get\s+text|transcribe|scan)\s+(?:text\s+from\s+)?(.+)",
        re.IGNORECASE,
    )),
    # Understand / Analyze image
    (Intent.UNDERSTAND, re.compile(
        r"(?:understand|analyze|analyse|describe|what(?:'s| is) in|explain|vision)\s+(.+)",
        re.IGNORECASE,
    )),
    # Batch process
    (Intent.BATCH, re.compile(
        r"(?:batch|process\s+(?:all|every|the)\s+(?:files?\s+)?(?:in\s+)?|process\s+folder\s+)(.+)",
        re.IGNORECASE,
    )),
    # Identify
    (Intent.IDENTIFY, re.compile(
        r"(?:identify|what\s+(?:type|kind|format)|detect\s+type|file\s+type)\s+(?:of\s+|is\s+)?(.+)",
        re.IGNORECASE,
    )),
    # Browse
    (Intent.BROWSE, re.compile(
        r"(?:browse|list|ls|dir|open|show|look\s+at|navigate\s+to|go\s+to|explore)\s+(?:folder\s+|directory\s+|dir\s+)?(.+)",
        re.IGNORECASE,
    )),
    # Tree
    (Intent.TREE, re.compile(
        r"(?:tree|structure|hierarchy)\s+(?:of\s+|for\s+)?(.+)",
        re.IGNORECASE,
    )),
    # Search
    (Intent.SEARCH, re.compile(
        r"(?:search|find|look\s+for)\s+(.+?)(?:\s+in\s+(.+))?$",
        re.IGNORECASE,
    )),
    # Config
    (Intent.CONFIG, re.compile(r"^(?:config|settings|configuration)$", re.IGNORECASE)),
    # Outputs
    (Intent.OUTPUTS, re.compile(r"^(?:outputs?|results?)$", re.IGNORECASE)),
    # Help
    (Intent.HELP, re.compile(r"^(?:help|commands|\?)$", re.IGNORECASE)),
    # Quit
    (Intent.QUIT, re.compile(r"^(?:quit|exit|bye|q)$", re.IGNORECASE)),
]


# =========================================================================
# Intent Parser
# =========================================================================

class NLParser:
    """Parse natural language input into structured intents."""

    def parse(self, user_input: str) -> dict[str, Any]:
        """Parse a natural language command.

        Args:
            user_input: Raw user input string.

        Returns:
            Dict with keys: intent, target (file/dir path), args (extra).
        """
        text = user_input.strip()
        if not text:
            return {"intent": Intent.UNKNOWN, "target": None, "args": {}}

        for intent, pattern in _PATTERNS:
            match = pattern.match(text)
            if match:
                groups = match.groups()
                target = groups[0].strip().strip("\"'") if groups else None
                extra = groups[1].strip().strip("\"'") if len(groups) > 1 and groups[1] else None

                return {
                    "intent": intent,
                    "target": target,
                    "args": {"extra": extra} if extra else {},
                }

        # Fallback: if just a path, try to determine intent from context
        clean = text.strip("\"'")
        p = Path(clean)
        if p.exists():
            if p.is_dir():
                return {"intent": Intent.BROWSE, "target": clean, "args": {}}
            elif p.is_file():
                return {"intent": Intent.EXTRACT, "target": clean, "args": {}}

        return {"intent": Intent.UNKNOWN, "target": text, "args": {}}


# =========================================================================
# Command Executor
# =========================================================================

class NLInterface:
    """Interactive natural language interface for the Omni-OCR Agent.

    Parses user commands and delegates them to the appropriate pipeline
    functions.
    """

    def __init__(self) -> None:
        self._parser = NLParser()
        self._engine = None  # Lazy-loaded
        self._browser = None
        self._batch = None

    def _get_engine(self):
        if self._engine is None:
            from interface import OmniOCREngine
            self._engine = OmniOCREngine()
        return self._engine

    def _get_browser(self):
        if self._browser is None:
            from folder_browser import FolderBrowser
            self._browser = FolderBrowser()
        return self._browser

    def _get_batch(self):
        if self._batch is None:
            from batch_processor import BatchProcessor
            self._batch = BatchProcessor()
        return self._batch

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    def run_interactive(self) -> None:
        """Start the interactive REPL loop."""
        self._print_banner()

        while True:
            try:
                user_input = input(f"\n{Fore.CYAN}🤖 omni>{Style.RESET_ALL} ").strip()
                if not user_input:
                    continue

                result = self.execute(user_input)
                if result is None:  # Quit signal
                    break

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Use 'quit' to exit.{Style.RESET_ALL}")
            except EOFError:
                break

        print(f"\n{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")

    def execute(self, user_input: str) -> Any:
        """Parse and execute a single command.

        Args:
            user_input: Natural language command.

        Returns:
            Result dict, or None to signal quit.
        """
        parsed = self._parser.parse(user_input)
        intent = parsed["intent"]
        target = parsed["target"]
        args = parsed["args"]

        handlers = {
            Intent.EXTRACT: self._handle_extract,
            Intent.UNDERSTAND: self._handle_understand,
            Intent.BATCH: self._handle_batch,
            Intent.IDENTIFY: self._handle_identify,
            Intent.BROWSE: self._handle_browse,
            Intent.TREE: self._handle_tree,
            Intent.SEARCH: self._handle_search,
            Intent.HELP: self._handle_help,
            Intent.CONFIG: self._handle_config,
            Intent.OUTPUTS: self._handle_outputs,
            Intent.QUIT: self._handle_quit,
        }

        handler = handlers.get(intent, self._handle_unknown)
        return handler(target, args)

    # ------------------------------------------------------------------
    # Command Handlers
    # ------------------------------------------------------------------

    def _handle_extract(self, target: str | None, args: dict) -> dict:
        """Extract text from a file."""
        if not target:
            self._error("Please provide a file path. Example: extract invoice.pdf")
            return {}

        self._info(f"Extracting text from: {target}")
        engine = self._get_engine()
        result = engine.extract_media(target)
        self._print_extraction_result(result)
        return result

    def _handle_understand(self, target: str | None, args: dict) -> dict:
        """Analyze / understand an image."""
        if not target:
            self._error("Please provide an image path. Example: understand photo.jpg")
            return {}

        self._info(f"Analyzing image: {target}")
        engine = self._get_engine()
        result = engine.understand_image(target)
        self._print_analysis_result(result)
        return result

    def _handle_batch(self, target: str | None, args: dict) -> dict:
        """Batch process a folder."""
        if not target:
            self._error("Please provide a folder path. Example: batch /data/scans")
            return {}

        self._info(f"Batch processing folder: {target}")
        engine = self._get_engine()
        batch = self._get_batch()

        def progress(current: int, total: int, filename: str) -> None:
            pct = int(current / total * 100) if total > 0 else 0
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(
                f"\r  {Fore.CYAN}[{bar}]{Style.RESET_ALL} "
                f"{current}/{total} ({pct}%) — {filename}",
                end="", flush=True,
            )

        result = batch.process_folder(
            target,
            extract_fn=engine.extract_media,
            progress_callback=progress,
        )
        print()  # Newline after progress bar
        self._print_batch_result(result)
        return result

    def _handle_identify(self, target: str | None, args: dict) -> dict:
        """Identify file type."""
        if not target:
            self._error("Please provide a file or folder path.")
            return {}

        from file_identifier import identify_file, identify_folder

        p = Path(target)
        if p.is_dir():
            result = identify_folder(str(p))
            self._print_folder_identification(result)
        elif p.is_file():
            result = identify_file(str(p))
            self._print_file_identification(result)
        else:
            self._error(f"Path not found: {target}")
            return {}

        return result

    def _handle_browse(self, target: str | None, args: dict) -> dict:
        """Browse a directory."""
        if not target:
            target = "."

        browser = self._get_browser()
        try:
            result = browser.browse(target)
            self._print_folder_listing(result)
            return result
        except NotADirectoryError:
            self._error(f"Not a directory: {target}")
            return {}

    def _handle_tree(self, target: str | None, args: dict) -> str:
        """Show directory tree."""
        if not target:
            target = "."

        browser = self._get_browser()
        tree_str = browser.tree(target)
        print(f"\n{tree_str}")
        return tree_str

    def _handle_search(self, target: str | None, args: dict) -> list:
        """Search for files."""
        if not target:
            self._error("Please specify what to search for.")
            return []

        search_dir = args.get("extra", ".")
        browser = self._get_browser()
        results = browser.search_files(search_dir, name_pattern=target)

        if results:
            self._success(f"Found {len(results)} file(s):")
            for info in results:
                cat_icon = self._category_icon(info["category"])
                print(
                    f"  {cat_icon} {info['file_name']}  "
                    f"({info['category']}, {info['size_human']})"
                )
                print(f"     📎 {info['file_path']}")
        else:
            self._warn(f"No files found matching '{target}'")

        return results

    def _handle_help(self, target: str | None, args: dict) -> None:
        """Show help text."""
        self._print_help()

    def _handle_config(self, target: str | None, args: dict) -> None:
        """Show current configuration summary."""
        from config import API, MODELS, OUTPUT_CFG, BATCH_CFG, SECURITY_CFG

        print(f"\n{Fore.CYAN}⚙  Configuration Summary{Style.RESET_ALL}")
        print(f"  {'API Base URL:':<25} {API.base_url}")
        print(f"  {'API Key Set:':<25} {'✅ Yes' if API.validate() else '❌ No'}")
        print(f"  {'Vision Model:':<25} {MODELS.vision}")
        print(f"  {'Audio Model:':<25} {MODELS.audio_asr}")
        print(f"  {'Agent LLM:':<25} {MODELS.agent_llm}")
        print(f"  {'Output Directory:':<25} {OUTPUT_CFG.base_dir}")
        print(f"  {'Save JSON:':<25} {OUTPUT_CFG.save_json}")
        print(f"  {'Save Text:':<25} {OUTPUT_CFG.save_text}")
        print(f"  {'Batch Workers:':<25} {BATCH_CFG.max_workers}")
        print(f"  {'Read-Only Mode:':<25} {'✅ Enforced' if SECURITY_CFG.read_only else '❌ Off'}")

    def _handle_outputs(self, target: str | None, args: dict) -> None:
        """List saved outputs."""
        from output_manager import output_mgr
        outputs = output_mgr.list_outputs()
        if outputs:
            self._success(f"Found {len(outputs)} output file(s):")
            for path in outputs[-20:]:  # Show last 20
                print(f"  📄 {path}")
            if len(outputs) > 20:
                print(f"  ... and {len(outputs) - 20} more")
        else:
            self._info("No outputs saved yet.")
        print(f"  📁 Output directory: {output_mgr.get_output_dir()}")

    def _handle_quit(self, target: str | None, args: dict) -> None:
        """Signal quit."""
        return None

    def _handle_unknown(self, target: str | None, args: dict) -> None:
        """Handle unrecognised commands."""
        self._warn(
            f"I didn't understand that command. "
            f"Type 'help' to see available commands."
        )

    # ------------------------------------------------------------------
    # Pretty Printers
    # ------------------------------------------------------------------

    def _print_banner(self) -> None:
        """Print the welcome banner."""
        print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   {Fore.WHITE}🔍  Omni-OCR Agent  —  Intelligent File Extraction{Fore.CYAN}        ║
║                                                              ║
║   {Fore.WHITE}Analyze images • Extract text • Process folders{Fore.CYAN}           ║
║   {Fore.WHITE}All operations are READ-ONLY on your files{Fore.CYAN}                ║
║                                                              ║
║   {Fore.YELLOW}Type 'help' for available commands{Fore.CYAN}                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")

    def _print_help(self) -> None:
        """Print available commands."""
        print(f"""
{Fore.CYAN}📖  Available Commands{Style.RESET_ALL}
{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}

  {Fore.GREEN}extract <file>{Style.RESET_ALL}          Extract text from a file (OCR/transcription)
  {Fore.GREEN}understand <image>{Style.RESET_ALL}      Analyze what's in an image (vision AI)
  {Fore.GREEN}batch <folder>{Style.RESET_ALL}          Process all files in a folder
  {Fore.GREEN}identify <file|folder>{Style.RESET_ALL}  Detect file type(s)
  {Fore.GREEN}browse <folder>{Style.RESET_ALL}         List folder contents with metadata
  {Fore.GREEN}tree <folder>{Style.RESET_ALL}           Show directory tree structure
  {Fore.GREEN}search <name> in <dir>{Style.RESET_ALL}  Find files by name
  {Fore.GREEN}config{Style.RESET_ALL}                  Show current configuration
  {Fore.GREEN}outputs{Style.RESET_ALL}                 List saved output files
  {Fore.GREEN}help{Style.RESET_ALL}                    Show this help message
  {Fore.GREEN}quit{Style.RESET_ALL}                    Exit the agent

{Fore.CYAN}💡  Natural Language Examples{Style.RESET_ALL}
{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}

  {Fore.YELLOW}"What's in this image? photo.jpg"{Style.RESET_ALL}
  {Fore.YELLOW}"Extract text from invoice.pdf"{Style.RESET_ALL}
  {Fore.YELLOW}"Process all files in /data/scans"{Style.RESET_ALL}
  {Fore.YELLOW}"What type is report.xlsx"{Style.RESET_ALL}
  {Fore.YELLOW}"Browse /data/documents"{Style.RESET_ALL}

{Fore.RED}🔒  Security: READ-ONLY access — no files will be modified{Style.RESET_ALL}
""")

    def _print_extraction_result(self, result: dict) -> None:
        """Pretty-print an extraction result."""
        status = "✅" if not result.get("error_log") else "❌"
        print(f"\n{Fore.CYAN}📋  Extraction Result  {status}{Style.RESET_ALL}")
        print(f"  {'File:':<20} {result.get('file_name', 'N/A')}")
        print(f"  {'Type:':<20} {result.get('media_type', 'N/A')}")
        print(f"  {'Method:':<20} {result.get('extraction_method', 'N/A')}")
        print(f"  {'Confidence:':<20} {result.get('confidence_score', 0):.0%}")

        if result.get("error_log"):
            print(f"  {Fore.RED}{'Error:':<20} {result['error_log'][:200]}{Style.RESET_ALL}")
        else:
            content = result.get("extracted_content", "")
            preview = content[:500] + ("..." if len(content) > 500 else "")
            print(f"\n  {Fore.GREEN}─── Extracted Content ───{Style.RESET_ALL}")
            print(f"  {preview}")

    def _print_analysis_result(self, result: dict) -> None:
        """Pretty-print a vision analysis result."""
        status = "✅" if not result.get("error_log") else "❌"
        print(f"\n{Fore.CYAN}🔍  Vision Analysis  {status}{Style.RESET_ALL}")
        print(f"  {'File:':<20} {result.get('file_name', 'N/A')}")
        print(f"  {'Model:':<20} {result.get('model_used', 'N/A')}")

        if result.get("error_log"):
            print(f"  {Fore.RED}{'Error:':<20} {result['error_log'][:200]}{Style.RESET_ALL}")
        else:
            analysis = result.get("analysis", "")
            print(f"\n  {Fore.GREEN}─── Analysis ───{Style.RESET_ALL}")
            print(f"  {analysis[:1000]}")

    def _print_batch_result(self, result: dict) -> None:
        """Pretty-print a batch processing result."""
        print(f"\n{Fore.CYAN}📦  Batch Processing Summary{Style.RESET_ALL}")
        print(f"  {'Directory:':<20} {result.get('directory', 'N/A')}")
        print(f"  {'Total Files:':<20} {result.get('total_files', 0)}")
        print(f"  {Fore.GREEN}{'Succeeded:':<20} {result.get('succeeded', 0)}{Style.RESET_ALL}")
        print(f"  {Fore.RED}{'Failed:':<20} {result.get('failed', 0)}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}{'Skipped:':<20} {result.get('skipped', 0)}{Style.RESET_ALL}")

        by_cat = result.get("by_category", {})
        if by_cat:
            print(f"\n  {Fore.CYAN}By Category:{Style.RESET_ALL}")
            for cat, count in sorted(by_cat.items()):
                icon = self._category_icon(cat)
                print(f"    {icon} {cat:<15} {count}")

        report_path = result.get("report_path")
        if report_path:
            print(f"\n  📄 Report: {report_path}")

    def _print_folder_listing(self, listing: dict) -> None:
        """Pretty-print a folder listing."""
        print(f"\n{Fore.CYAN}📁  {listing.get('directory', '')}{Style.RESET_ALL}")
        print(
            f"  {listing.get('directories', 0)} directories, "
            f"{listing.get('files', 0)} files"
        )
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")

        for entry in listing.get("entries", []):
            if entry.get("is_dir"):
                count = entry.get("child_count", "?")
                print(f"  📁 {Fore.BLUE}{entry['name']}/{Style.RESET_ALL}  ({count} items)")
            else:
                icon = self._category_icon(entry.get("category", "unknown"))
                size = entry.get("size_human", "?")
                cat = entry.get("category", "")
                print(f"  {icon} {entry['name']}  ({cat}, {size})")

    def _print_file_identification(self, info: dict) -> None:
        """Pretty-print a file identification result."""
        icon = self._category_icon(info.get("category", "unknown"))
        supported = "✅ Supported" if info.get("is_supported") else "⚠️  Not extractable"

        print(f"\n{icon}  {Fore.CYAN}File Identification{Style.RESET_ALL}")
        print(f"  {'Name:':<20} {info.get('file_name', 'N/A')}")
        print(f"  {'Category:':<20} {info.get('category', 'unknown')}")
        print(f"  {'Extension:':<20} {info.get('extension', 'N/A')}")
        print(f"  {'MIME Type:':<20} {info.get('mime_type', 'N/A')}")
        print(f"  {'Size:':<20} {info.get('size_human', 'N/A')}")
        print(f"  {'Pipeline:':<20} {supported}")

    def _print_folder_identification(self, result: dict) -> None:
        """Pretty-print a folder identification summary."""
        print(f"\n{Fore.CYAN}📁  Folder Analysis: {result.get('directory', '')}{Style.RESET_ALL}")
        print(f"  {'Total Files:':<20} {result.get('total_files', 0)}")
        print(f"  {Fore.GREEN}{'Supported:':<20} {result.get('supported_count', 0)}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}{'Unsupported:':<20} {result.get('unsupported_count', 0)}{Style.RESET_ALL}")

        by_cat = result.get("by_category", {})
        if by_cat:
            print(f"\n  {Fore.CYAN}Breakdown:{Style.RESET_ALL}")
            for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
                icon = self._category_icon(cat)
                print(f"    {icon} {cat:<15} {count}")

    # ------------------------------------------------------------------
    # Formatting Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _category_icon(category: str) -> str:
        """Return an emoji icon for a file category."""
        icons = {
            "image": "🖼️ ",
            "document": "📄",
            "spreadsheet": "📊",
            "presentation": "📽️ ",
            "audio": "🎵",
            "video": "🎬",
            "code": "💻",
            "archive": "📦",
            "unknown": "❓",
        }
        return icons.get(category, "📄")

    @staticmethod
    def _info(msg: str) -> None:
        print(f"  {Fore.CYAN}ℹ  {msg}{Style.RESET_ALL}")

    @staticmethod
    def _success(msg: str) -> None:
        print(f"  {Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

    @staticmethod
    def _warn(msg: str) -> None:
        print(f"  {Fore.YELLOW}⚠  {msg}{Style.RESET_ALL}")

    @staticmethod
    def _error(msg: str) -> None:
        print(f"  {Fore.RED}❌ {msg}{Style.RESET_ALL}")
