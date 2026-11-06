"""Compute a confidence score for a slide's extraction quality."""

from __future__ import annotations

from slidebridge.constants import (
    CONFIDENCE_PENALTY_CHART_HEAVY,
    CONFIDENCE_PENALTY_GROUPED_SHAPES,
    CONFIDENCE_PENALTY_MANY_FRAGMENTS,
    CONFIDENCE_PENALTY_NO_TITLE,
    CONFIDENCE_PENALTY_ZERO_TEXT_NONBLANK_IMAGE,
)
from slidebridge.models.slide import SlideRecord

_MANY_FRAGMENTS_THRESHOLD = 8
_SHORT_BLOCK_CHARS = 15


def score_slide(slide: SlideRecord) -> SlideRecord:
    """Apply penalty-based scoring and return updated SlideRecord."""
    score = 1.0

    if slide.title_source == "fallback":
        score -= CONFIDENCE_PENALTY_NO_TITLE

    # Zero text but image exists (image_path set or shapes present)
    if slide.raw_text_char_count == 0 and slide.shape_count > 0:
        score -= CONFIDENCE_PENALTY_ZERO_TEXT_NONBLANK_IMAGE

    # High ratio of small fragments
    short_blocks = [b for b in slide.text_blocks if len(b.text) < _SHORT_BLOCK_CHARS]
    if len(short_blocks) >= _MANY_FRAGMENTS_THRESHOLD:
        score -= CONFIDENCE_PENALTY_MANY_FRAGMENTS

    # Grouped shapes present
    group_blocks = [b for b in slide.text_blocks if b.shape_type == "GROUP"]
    if group_blocks:
        score -= CONFIDENCE_PENALTY_GROUPED_SHAPES

    # Possible chart-heavy: many shapes but low text
    if slide.shape_count > 5 and slide.raw_text_char_count < 50:
        score -= CONFIDENCE_PENALTY_CHART_HEAVY

    score = max(0.0, round(score, 2))
    return slide.model_copy(update={"confidence": score})
