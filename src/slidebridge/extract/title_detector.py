"""Detect the title of a slide with a fallback hierarchy."""

from __future__ import annotations

from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.slide import Slide

from slidebridge.models.shape import TextBlock

_TITLE_PH_TYPES = {
    PP_PLACEHOLDER.TITLE,
    PP_PLACEHOLDER.CENTER_TITLE,
    PP_PLACEHOLDER.VERTICAL_TITLE,
}


def detect_title(slide: Slide, blocks: list[TextBlock]) -> tuple[str, str]:
    """Return (title_text, title_source) using a 3-tier fallback.

    1. Placeholder — TITLE / CENTER_TITLE / VERTICAL_TITLE type
    2. TextBlock with role == "title" (from shape_classifier)
    3. First non-empty text block heuristic
    """
    # Tier 1: native placeholder
    for shape in slide.shapes:
        if shape.is_placeholder and shape.placeholder_format.type in _TITLE_PH_TYPES:
            text = shape.text_frame.text.strip() if shape.has_text_frame else ""
            if text:
                return text, "placeholder"

    # Tier 2: classified title block
    for block in blocks:
        if block.role == "title" and block.text.strip():
            return block.text.strip(), "textbox"

    # Tier 3: first non-empty block
    for block in blocks:
        if block.text.strip():
            return block.text.strip()[:120], "inferred"

    return "", "fallback"
