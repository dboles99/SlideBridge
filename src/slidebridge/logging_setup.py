"""Logging configuration for SlideBridge.

Sets up console (rich) + file handlers (run.log / errors.log).
Call configure_logging() once at CLI startup.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

_configured = False


def configure_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
) -> None:
    """Configure root logger with console and optional file handlers."""
    global _configured
    if _configured:
        return
    _configured = True

    level = getattr(logging, log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Rich console handler — force UTF-8 and disable Win32 legacy console so
    # that box-drawing characters in log messages don't crash on cp1252 systems.
    rich_console = Console(
        stderr=True,
        file=sys.stderr,
        force_terminal=True,
        legacy_windows=False,
    )
    console = RichHandler(
        console=rich_console,
        level=level,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )
    console.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    root.addHandler(console)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        _add_file_handler(root, log_dir / "run.log", level)
        _add_file_handler(root, log_dir / "errors.log", logging.ERROR)


def _add_file_handler(root: logging.Logger, path: Path, level: int) -> None:
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(fh)
