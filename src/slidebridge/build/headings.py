"""Add a Heading 1 entry for a slide section."""

from __future__ import annotations

import re

from docx import Document

from slidebridge.models.slide import SlideRecord

# Strip XML 1.0-incompatible control characters (keep tab, LF, CR)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize(text: str) -> str:
    """Remove control characters that are illegal in XML 1.0."""
    return _CTRL_RE.sub("", text)


def add_slide_heading(doc: Document, slide: SlideRecord) -> None:
    """Insert a Heading 1 paragraph: 'Slide N - Title'."""
    heading_text = _sanitize(f"Slide {slide.slide_number} - {slide.title}")
    doc.add_heading(heading_text, level=1)
