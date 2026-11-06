"""Merge small adjacent text fragments within a slide's text block list.

This is a standalone module so it can be called independently of the full
reading-order sort.  The same logic is also invoked via reorder_slide() in
reading_order.py when merge_fragments=True.
"""

from __future__ import annotations

from slidebridge.models.shape import TextBlock

_FRAGMENT_THRESHOLD = 20  # chars — blocks shorter than this are candidates


def merge_fragments(blocks: list[TextBlock], threshold: int = _FRAGMENT_THRESHOLD) -> list[TextBlock]:
    """Merge adjacent short non-table blocks into their successor.

    Rules:
    - Only body blocks shorter than *threshold* chars are merged.
    - Table blocks are never merged (they are atomic units).
    - Footer blocks are never merged into other footers.
    - Merging preserves the successor block's ``bbox`` and ``role``.
    - The combined ``paragraphs`` list is the concatenation of both blocks.

    Returns a new list; the input is not mutated.
    """
    if len(blocks) < 2:
        return list(blocks)

    merged: list[TextBlock] = []
    i = 0
    while i < len(blocks):
        current = blocks[i]
        if (
            len(current.text) < threshold
            and current.role not in ("table", "footer")
            and i + 1 < len(blocks)
            and blocks[i + 1].role not in ("table",)
        ):
            nxt = blocks[i + 1]
            combined_text = current.text.rstrip() + "\n" + nxt.text
            merged_block = nxt.model_copy(
                update={
                    "text": combined_text,
                    "paragraphs": current.paragraphs + nxt.paragraphs,
                }
            )
            merged.append(merged_block)
            i += 2
        else:
            merged.append(current)
            i += 1

    return merged
