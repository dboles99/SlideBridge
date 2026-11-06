"""Audit row model — one per slide, written to slides.csv."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuditRow(BaseModel):
    source_file: str
    slide_number: int
    title: str
    image_exists: bool
    text_shape_count: int = Field(ge=0)
    raw_text_char_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    warning_count: int = Field(ge=0)
    warnings: str  # semicolon-separated warning flag names
