"""Extract speaker notes from a slide."""

from __future__ import annotations

from pptx.slide import Slide


def extract_notes(slide: Slide) -> str:
    """Return the speaker notes text for a slide, or empty string."""
    try:
        if not slide.has_notes_slide:
            return ""
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        return tf.text.strip() if tf else ""
    except Exception:
        return ""
