"""
Structured JSON logger for Omni Browser Agent.
Provides Rich console output and JSON file logging with component-aware prefixes.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler


class ComponentFilter(logging.Filter):
    """Filter to add component name to log records."""

    def __init__(self, component: str = ""):
        super().__init__()
        self.component = component

    def filter(self, record: logging.LogRecord) -> bool:
        record.component = self.component
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "component": getattr(record, "component", "unknown"),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "component",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry)


def setup_logger(
    name: str,
    component: str = None,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_enabled: bool = True,
    json_file_enabled: bool = True,
) -> logging.Logger:
    """
    Set up a logger with Rich console output and optional JSON file logging.

    Args:
        name: Logger name
        component: Component name for log prefixing
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, defaults to logs/{name}.log)
        console_enabled: Whether to enable console output
        json_file_enabled: Whether to enable JSON file logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers
    logger.handlers.clear()

    # Set component name
    if component is None:
        component = name

    # Console handler with Rich
    if console_enabled:
        console = Console(stderr=True)
        rich_handler = RichHandler(
            console=console, show_time=True, show_path=True, markup=True
        )
        rich_handler.setFormatter(
            logging.Formatter(f"[{component}] %(message)s", datefmt="[%X]")
        )
        rich_handler.addFilter(ComponentFilter(component))
        logger.addHandler(rich_handler)

    # JSON file handler
    if json_file_enabled:
        if log_file is None:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = str(log_dir / f"{name}.log")

        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(JSONFormatter())
        file_handler.addFilter(ComponentFilter(component))
        logger.addHandler(file_handler)

    return logger


# Component-specific logger factory
def get_component_logger(component_name: str) -> logging.Logger:
    """
    Get a logger for a specific component.

    Args:
        component_name: Name of the component (e.g., 'browser', 'auth', 'pipeline')

    Returns:
        Logger instance configured for the component
    """
    from core.config import get_settings

    settings = get_settings()

    return setup_logger(
        name=f"omni_browser.{component_name}",
        component=component_name,
        log_level=settings.log_level,
        log_file="logs/omni_browser.log",
        console_enabled=True,
        json_file_enabled=True,
    )
