"""Alignment pipeline: review_pack.docx + edited.docx → aligned.docx.

Strategy
--------
1. Parse review pack → slide sections with original-text rows.
2. Read edited DOCX → flat text.
3. Segment edited text into matchable units.
4. For every original row, find the best edited match.
5. Copy the review pack to output path, then update the Edited Text and
   Notes cells in each table in-place (images and layout are preserved).
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docx import Document

from slidebridge.align.docx_reader import ParsedSlide, parse_review_pack, read_edited_doc
from slidebridge.align.matcher import find_best_match
from slidebridge.align.segment import build_segments

logger = logging.getLogger(__name__)


@dataclass
class AlignStats:
    total: int = 0
    exact: int = 0
    fuzzy: int = 0
    window: int = 0
    contained: int = 0
    not_found: int = 0
    by_change_type: dict[str, int] = field(default_factory=dict)

    def record(self, strategy: str, change_type: str) -> None:
        self.total += 1
        counter = getattr(self, strategy, None)
        if counter is not None:
            setattr(self, strategy, counter + 1)
        elif strategy != "none":
            pass
        if change_type == "Not Found":
            self.not_found += 1
        self.by_change_type[change_type] = self.by_change_type.get(change_type, 0) + 1


def run_alignment(
    review_pack_path: Path,
    edited_doc_path: Path,
    output_path: Path,
) -> AlignStats:
    """Run the full alignment and write to *output_path*. Returns stats."""
    logger.info("Alignment start: %s + %s", review_pack_path.name, edited_doc_path.name)

    # -- Parse --
    slides = parse_review_pack(review_pack_path)
    edited_text = read_edited_doc(edited_doc_path)
    segments = build_segments(edited_text)

    logger.info("Edited doc: %d segments", len(segments))

    # -- Match --
    stats = AlignStats()
    for slide in slides:
        for row in slide.rows:
            result = find_best_match(row.original_text, segments)
            row.edited_text = result.matched_text
            row.change_type = result.change_type
            row.notes_suffix = result.notes
            stats.record(result.strategy, result.change_type)

    logger.info(
        "Match results: %d total, %d not-found, %d exact, %d fuzzy, %d window",
        stats.total, stats.not_found, stats.exact, stats.fuzzy, stats.window,
    )

    # -- Write --
    _write_aligned(review_pack_path, slides, output_path)
    logger.info("Aligned DOCX written -> %s", output_path)
    return stats


def _write_aligned(
    source_path: Path,
    slides: list[ParsedSlide],
    output_path: Path,
) -> None:
    """Copy source DOCX to output_path and update table cells in-place."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, output_path)

    doc = Document(str(output_path))

    for slide in slides:
        if slide.table_idx < 0 or slide.table_idx >= len(doc.tables):
            logger.warning("Slide %d: table index %d out of range", slide.slide_number, slide.table_idx)
            continue

        table = doc.tables[slide.table_idx]

        for row in slide.rows:
            if row.table_row_idx >= len(table.rows):
                continue
            tr = table.rows[row.table_row_idx]
            cells = tr.cells

            # Populate Edited Text column
            if row.col_edited != -1 and row.col_edited < len(cells):
                _set_cell(cells[row.col_edited], row.edited_text)

            # Prepend change_type to Notes column
            if row.col_notes != -1 and row.col_notes < len(cells):
                existing = cells[row.col_notes].text.strip()
                new_notes = _format_notes(row.change_type, row.notes_suffix, existing)
                _set_cell(cells[row.col_notes], new_notes)

    doc.save(str(output_path))


def _set_cell(cell: Any, text: str) -> None:
    """Clear a table cell and set its text."""
    for para in cell.paragraphs:
        for run in para.runs:
            run.text = ""

    # Some cells may have a paragraph with no runs; handle both cases safely.
    para = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()

    if para.runs:
        para.runs[0].text = text
    else:
        para.add_run(text)


def _format_notes(change_type: str, match_notes: str, existing: str) -> str:
    """Build the notes cell content."""
    if change_type == "Unchanged" and existing:
        return existing   # don't clutter unchanged rows
    parts = [p for p in [change_type, match_notes, existing] if p]
    return " | ".join(parts)
