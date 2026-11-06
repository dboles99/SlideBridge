"""Add the 4-column editable review table to a DOCX document."""

from __future__ import annotations

import re

from docx import Document
from docx.shared import Inches

from slidebridge.constants import (
    COL_EDITED_WIDTH,
    COL_NOTES_WIDTH,
    COL_ORDER_WIDTH,
    COL_ORIGINAL_WIDTH,
)
from slidebridge.models.slide import SlideRecord

_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _s(text: str) -> str:
    """Strip XML 1.0-incompatible control characters."""
    return _CTRL_RE.sub("", text)

_HEADERS = ("Order", "Original Extracted Text", "Edited Text", "Notes")
_COL_WIDTHS = (COL_ORDER_WIDTH, COL_ORIGINAL_WIDTH, COL_EDITED_WIDTH, COL_NOTES_WIDTH)


def add_text_table(doc: Document, slide: SlideRecord) -> None:
    """Insert an editable 4-column table with one row per text block."""
    blocks = slide.text_blocks
    row_count = max(len(blocks), 1)  # always at least one data row

    table = doc.add_table(rows=1 + row_count, cols=4)
    table.style = "Table Grid"

    # Header row
    hdr_cells = table.rows[0].cells
    for col_idx, (header, width) in enumerate(zip(_HEADERS, _COL_WIDTHS, strict=True)):
        cell = hdr_cells[col_idx]
        cell.text = header
        cell.width = Inches(width)
        run = cell.paragraphs[0].runs[0]
        run.bold = True

    # Data rows
    for row_idx, block in enumerate(blocks, start=1):
        row_cells = table.rows[row_idx].cells
        row_cells[0].text = str(block.order)
        row_cells[1].text = _s(block.text)
        row_cells[2].text = ""   # Edited Text — left blank for editor
        row_cells[3].text = _s(block.role)

    # If no blocks, leave one empty row with a note
    if not blocks:
        row_cells = table.rows[1].cells
        row_cells[0].text = "—"
        row_cells[1].text = "(no text extracted)"
        row_cells[2].text = ""
        row_cells[3].text = ""
