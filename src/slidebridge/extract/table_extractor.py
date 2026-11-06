"""Extract text from table shapes, preserving row/cell structure."""

from __future__ import annotations

from pptx.shapes.base import BaseShape

from slidebridge.models.shape import BoundingBox, TextBlock, TextRun


def extract_table_blocks(
    shape: BaseShape,
    slide_uid: str,
    start_order: int = 1,
) -> list[TextBlock]:
    """Return one TextBlock per table row, with cells joined by ' | '.

    The entire table is also emitted as a single block with role="table".
    """
    if not shape.has_table:
        return []

    table = shape.table
    row_texts: list[str] = []

    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
        if cells:
            row_texts.append(" | ".join(cells))

    if not row_texts:
        return []

    full_text = "\n".join(row_texts)

    block = TextBlock(
        block_id=f"{slide_uid}-tbl{start_order:03d}",
        order=start_order,
        shape_id=shape.shape_id,
        shape_type="TABLE",
        role="table",
        bbox=BoundingBox(
            left=shape.left or 0,
            top=shape.top or 0,
            width=shape.width or 0,
            height=shape.height or 0,
        ),
        text=full_text,
        paragraphs=row_texts,
        runs=[TextRun(text=full_text)],
    )
    return [block]
