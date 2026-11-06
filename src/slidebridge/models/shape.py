"""Shape and bounding-box models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Position and size in EMUs (English Metric Units)."""

    left: int
    top: int
    width: int
    height: int


class TextRun(BaseModel):
    text: str
    bold: bool = False
    italic: bool = False


class TextBlock(BaseModel):
    """A single text-bearing shape or table cell group, in reading order."""

    block_id: str
    order: int = Field(ge=1)
    shape_id: int | None = None
    shape_type: str  # e.g. PLACEHOLDER, TEXT_BOX, TABLE, GROUP
    role: str = "body"  # title | body | footer | notes | table
    bbox: BoundingBox
    text: str
    paragraphs: list[str] = Field(default_factory=list)
    runs: list[TextRun] = Field(default_factory=list)
