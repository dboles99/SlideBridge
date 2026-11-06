"""Configuration loading for SlideBridge.

Loads from slidebridge.yaml (or --config path) with sensible defaults.
All values are overridable via CLI flags.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from slidebridge.constants import (
    DEFAULT_DPI,
    DEFAULT_IMAGE_FORMAT,
    IMAGE_WIDTH_INCHES,
    MAX_IMAGE_WIDTH_PX,
    ROW_TOLERANCE_EMU,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_NAME = "slidebridge.yaml"


class RenderConfig(BaseModel):
    engine: str = "libreoffice"
    dpi: int = Field(DEFAULT_DPI, ge=72, le=600)
    image_format: str = DEFAULT_IMAGE_FORMAT
    optimize_images: bool = True
    max_width_px: int = Field(MAX_IMAGE_WIDTH_PX, ge=400)


class ExtractConfig(BaseModel):
    include_notes: bool = True
    detect_titles: bool = True
    merge_text_fragments: bool = True


class ReconcileConfig(BaseModel):
    sort_primary: str = "top"
    sort_secondary: str = "left"
    row_tolerance_emu: int = Field(ROW_TOLERANCE_EMU, ge=0)
    warn_low_confidence: bool = True


class DocxConfig(BaseModel):
    page_size: str = "A4"
    margins: str = "narrow"
    insert_source_filename: bool = True
    image_width_inches: float = Field(IMAGE_WIDTH_INCHES, ge=1.0, le=10.0)
    table_layout: str = "fixed"
    include_warning_block: bool = True


class AuditConfig(BaseModel):
    write_csv: bool = True
    write_json: bool = True


class ProjectConfig(BaseModel):
    name: str = "slidebridge"
    log_level: str = "INFO"


class SlideBridgeConfig(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    extract: ExtractConfig = Field(default_factory=ExtractConfig)
    reconcile: ReconcileConfig = Field(default_factory=ReconcileConfig)
    docx: DocxConfig = Field(default_factory=DocxConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)


def load_config(path: Path | None = None) -> SlideBridgeConfig:
    """Load config from YAML file, falling back to defaults if not found."""
    candidates = [path] if path else [Path(DEFAULT_CONFIG_NAME)]

    for candidate in candidates:
        if candidate and candidate.exists():
            logger.debug("Loading config from %s", candidate)
            raw: dict[str, Any] = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            return SlideBridgeConfig.model_validate(raw)

    logger.debug("No config file found; using defaults")
    return SlideBridgeConfig()
