"""Extract TextBlock objects from a single text-frame shape."""

from __future__ import annotations

from pptx.shapes.base import BaseShape

from slidebridge.models.shape import BoundingBox, TextBlock, TextRun


def extract_text_blocks(
    shape: BaseShape,
    slide_uid: str,
    role: str,
    start_order: int = 1,
) -> list[TextBlock]:
    """Return a list of TextBlock objects from a shape with a text frame.

    For most shapes this is a single block. We return a list to keep the
    interface uniform with table extraction.
    """
    if not shape.has_text_frame:
        return []

    paragraphs: list[str] = []
    runs: list[TextRun] = []

    for para in shape.text_frame.paragraphs:
        para_text = para.text
        if para_text:
            paragraphs.append(para_text)
        for run in para.runs:
            if run.text:
                runs.append(
                    TextRun(
                        text=run.text,
                        bold=bool(run.font.bold),
                        italic=bool(run.font.italic),
                    )
                )

    full_text = "\n".join(paragraphs)
    if not full_text.strip():
        return []

    block = TextBlock(
        block_id=f"{slide_uid}-b{start_order:03d}",
        order=start_order,
        shape_id=shape.shape_id,
        shape_type=shape.shape_type.name if hasattr(shape.shape_type, "name") else str(shape.shape_type),
        role=role,
        bbox=BoundingBox(
            left=shape.left or 0,
            top=shape.top or 0,
            width=shape.width or 0,
            height=shape.height or 0,
        ),
        text=full_text,
        paragraphs=paragraphs,
        runs=runs,
    )
    return [block]
