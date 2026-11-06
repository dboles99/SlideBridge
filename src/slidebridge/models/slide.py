"""Slide record model — one per slide in the pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from slidebridge.models.shape import TextBlock

TitleSource = Literal["placeholder", "textbox", "inferred", "fallback"]

WARNING_FLAGS = {
    "no_detected_title",
    "image_without_text",
    "possible_missing_chart_labels",
    "many_small_text_fragments",
    "grouped_shapes_present",
    "unsupported_shape_type_present",
    "notes_present_not_extracted",
    "table_detected",
    "confidence_below_threshold",
}


class SlideRecord(BaseModel):
    """Full structured record for one slide, produced by the extract stage."""

    source_file: str
    source_file_index: int = Field(ge=1)
    slide_number: int = Field(ge=1)
    slide_uid: str  # e.g. "part1-slide-012"

    title: str
    title_source: TitleSource = "fallback"

    image_path: str = ""          # filled after render stage
    pdf_page_number: int | None = None

    notes_present: bool = False
    notes_text: str = ""

    raw_text_char_count: int = Field(default=0, ge=0)
    ordered_text_char_count: int = Field(default=0, ge=0)
    shape_count: int = Field(default=0, ge=0)
    text_shape_count: int = Field(default=0, ge=0)
    table_count: int = Field(default=0, ge=0)

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)

    text_blocks: list[TextBlock] = Field(default_factory=list)
