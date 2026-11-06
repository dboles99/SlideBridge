"""Generate warning flags for a slide."""

from __future__ import annotations

from slidebridge.constants import CONFIDENCE_LOW_THRESHOLD
from slidebridge.models.slide import SlideRecord


def flag_slide(slide: SlideRecord, warn_low_confidence: bool = True) -> SlideRecord:
    """Attach warning flags based on slide properties. Returns updated record."""
    flags: list[str] = list(slide.warnings)

    if slide.title_source == "fallback":
        _add(flags, "no_detected_title")

    if slide.raw_text_char_count == 0 and slide.shape_count > 0:
        _add(flags, "image_without_text")

    group_shapes = [b for b in slide.text_blocks if b.shape_type == "GROUP"]
    if group_shapes:
        _add(flags, "grouped_shapes_present")

    if slide.table_count > 0:
        _add(flags, "table_detected")

    if slide.notes_present and not slide.notes_text.strip():
        _add(flags, "notes_present_not_extracted")

    # Chart heuristic: many shapes, low text
    if slide.shape_count > 5 and slide.raw_text_char_count < 50:
        _add(flags, "possible_missing_chart_labels")

    if warn_low_confidence and slide.confidence < CONFIDENCE_LOW_THRESHOLD:
        _add(flags, "confidence_below_threshold")

    return slide.model_copy(update={"warnings": flags})


def _add(flags: list[str], flag: str) -> None:
    if flag not in flags:
        flags.append(flag)
