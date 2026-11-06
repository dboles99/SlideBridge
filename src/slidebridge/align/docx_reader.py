"""Read a SlideBridge review-pack DOCX and an edited DOCX for alignment.

The review-pack structure (produced by build/docx_builder.py) is:
  Heading 1  "Slide N - Title"
  Normal     metadata line
  (image)
  (warning block, optional)
  Table      4 cols: Order | Original Extracted Text | Edited Text | Notes
  Page break

We iterate body elements in document order so headings and tables are
associated correctly even if the document has varying numbers of paragraphs
between them.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from docx import Document as open_docx
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)

# Column name variants (lower-cased for matching)
_COL_ORDER    = {"order"}
_COL_ORIGINAL = {"original extracted text", "original"}
_COL_EDITED   = {"edited text", "edited"}
_COL_NOTES    = {"notes"}

_HEADING_RE = re.compile(r"^Slide\s+(\d+)\s+-\s+(.+)$", re.IGNORECASE)


@dataclass
class ParsedRow:
    table_row_idx: int   # 1-based (row 0 is header)
    order: int
    original_text: str
    col_edited: int      # column index for "Edited Text"
    col_notes: int       # column index for "Notes"
    # filled by pipeline:
    edited_text: str = ""
    change_type: str = ""
    notes_suffix: str = ""   # prepended to existing notes content


@dataclass
class ParsedSlide:
    slide_number: int
    title: str
    table_idx: int       # index into doc.tables
    rows: list[ParsedRow] = field(default_factory=list)


def _iter_blocks(doc: DocxDocument) -> Iterator[Paragraph | Table]:
    """Yield Paragraph and Table objects in body order."""
    doc_any = cast(Any, doc)
    body = doc_any.element.body
    doc_body = doc_any._body

    for child in body:
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc_body)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc_body)


def _col_map(header_row: Any) -> dict[str, int]:
    """Return a lower-cased column-name → index map from the header row."""
    return {
        cell.text.strip().lower(): idx
        for idx, cell in enumerate(header_row.cells)
    }


def _find_col(col_map: dict[str, int], candidates: set[str]) -> int:
    for name in candidates:
        if name in col_map:
            return col_map[name]
    return -1


def parse_review_pack(path: Path | str) -> list[ParsedSlide]:
    """Return ordered ParsedSlide objects from a review-pack DOCX."""
    doc = open_docx(str(path))
    slides: list[ParsedSlide] = []
    table_counter = 0

    current_slide: ParsedSlide | None = None

    for block in _iter_blocks(doc):
        if isinstance(block, Paragraph):
            style_name = block.style.name if block.style else ""
            if "Heading 1" in style_name:
                m = _HEADING_RE.match(block.text.strip())
                if m:
                    current_slide = ParsedSlide(
                        slide_number=int(m.group(1)),
                        title=m.group(2).strip(),
                        table_idx=-1,
                    )
                    slides.append(current_slide)

        elif isinstance(block, Table):
            tbl_idx = table_counter
            table_counter += 1

            if current_slide is not None and current_slide.table_idx == -1:
                current_slide.table_idx = tbl_idx

                rows = block.rows
                if not rows:
                    continue

                cm = _col_map(rows[0])
                c_orig = _find_col(cm, _COL_ORIGINAL)
                c_edit = _find_col(cm, _COL_EDITED)
                c_note = _find_col(cm, _COL_NOTES)

                if c_orig == -1:
                    logger.warning(
                        "Slide %d table has no 'Original Extracted Text' column",
                        current_slide.slide_number,
                    )
                    continue

                for row_idx, row in enumerate(rows[1:], start=1):
                    cells = [c.text.strip() for c in row.cells]
                    if not any(cells):
                        continue
                    orig = cells[c_orig] if c_orig < len(cells) else ""
                    if not orig or orig == "(no text extracted)":
                        continue
                    try:
                        order = int(cells[0]) if cells[0].isdigit() else row_idx
                    except (ValueError, IndexError):
                        order = row_idx

                    current_slide.rows.append(ParsedRow(
                        table_row_idx=row_idx,
                        order=order,
                        original_text=orig,
                        col_edited=c_edit,
                        col_notes=c_note,
                    ))

    logger.info(
        "Parsed review pack: %d slides, %d total rows",
        len(slides),
        sum(len(s.rows) for s in slides),
    )
    return slides


def read_edited_doc(path: Path | str) -> str:
    """Extract all body text from an edited DOCX as a single string."""
    doc = open_docx(str(path))
    chunks: list[str] = []

    for block in _iter_blocks(doc):
        if isinstance(block, Paragraph):
            t = block.text.strip()
            if t:
                chunks.append(t)
        elif isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    t = cell.text.strip()
                    if t:
                        chunks.append(t)

    return "\n".join(chunks)
