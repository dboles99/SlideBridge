"""Reorder text blocks within a slide into approximate reading order.

Heuristic:
  1. Title block always first.
  2. Group remaining shapes into horizontal row bands by top position.
  3. Within each band sort by left position (left-to-right).
  4. Table blocks treated as atomic units.
  5. Footer-like blocks last.
"""

from __future__ import annotations

from slidebridge.constants import ROW_TOLERANCE_EMU
from slidebridge.models.shape import TextBlock
from slidebridge.models.slide import SlideRecord


def reorder_slide(slide: SlideRecord, merge_fragments: bool = True) -> SlideRecord:
    """Return a new SlideRecord with text_blocks sorted into reading order."""
    blocks = slide.text_blocks
    if not blocks:
        return slide

    titles = [b for b in blocks if b.role == "title"]
    footers = [b for b in blocks if b.role == "footer"]
    body = [b for b in blocks if b.role not in ("title", "footer")]

    sorted_body = _sort_by_position(body)
    if merge_fragments:
        from slidebridge.reconcile.chunk_merger import merge_fragments as _merge
        sorted_body = _merge(sorted_body)

    ordered = titles + sorted_body + footers

    # Re-assign order numbers
    for i, block in enumerate(ordered, start=1):
        block = block.model_copy(update={"order": i})
        ordered[i - 1] = block

    # Compute ordered char count
    ordered_chars = sum(len(b.text) for b in ordered)

    return slide.model_copy(
        update={
            "text_blocks": ordered,
            "ordered_text_char_count": ordered_chars,
        }
    )


def _sort_by_position(blocks: list[TextBlock]) -> list[TextBlock]:
    """Sort by top (banded) then left."""
    if not blocks:
        return blocks

    # Group into row bands
    sorted_by_top = sorted(blocks, key=lambda b: b.bbox.top)
    bands: list[list[TextBlock]] = []
    current_band: list[TextBlock] = [sorted_by_top[0]]

    for block in sorted_by_top[1:]:
        band_top = current_band[0].bbox.top
        if abs(block.bbox.top - band_top) <= ROW_TOLERANCE_EMU:
            current_band.append(block)
        else:
            bands.append(sorted(current_band, key=lambda b: b.bbox.left))
            current_band = [block]
    bands.append(sorted(current_band, key=lambda b: b.bbox.left))

    return [block for band in bands for block in band]
