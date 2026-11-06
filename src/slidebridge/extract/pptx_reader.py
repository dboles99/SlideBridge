"""PPTX deck reader — entry point for the extraction stage.

Walks all slides in source order and returns a list of SlideRecord objects
with raw (unordered) text blocks populated.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pptx import Presentation

from slidebridge.extract.notes_extractor import extract_notes
from slidebridge.extract.shape_classifier import classify_shape
from slidebridge.extract.table_extractor import extract_table_blocks
from slidebridge.extract.text_extractor import extract_text_blocks
from slidebridge.extract.title_detector import detect_title
from slidebridge.models.shape import TextBlock
from slidebridge.models.slide import SlideRecord

logger = logging.getLogger(__name__)


def extract_deck(
    pptx_path: Path,
    file_index: int,
    include_notes: bool = False,
    detect_titles: bool = True,
) -> list[SlideRecord]:
    """Open a PPTX and extract all slides. Returns ordered list of SlideRecord."""
    try:
        prs = Presentation(str(pptx_path))
    except Exception as exc:
        raise RuntimeError(f"Cannot open {pptx_path}: {exc}") from exc

    records: list[SlideRecord] = []
    source_name = pptx_path.name

    for slide_idx, slide in enumerate(prs.slides, start=1):
        uid = f"{pptx_path.stem}-slide-{slide_idx:03d}"
        logger.debug("Extracting slide %d of %s", slide_idx, source_name)

        blocks: list[TextBlock] = []
        block_counter = 0
        shape_count = 0
        text_shape_count = 0
        table_count = 0

        for shape in slide.shapes:
            shape_count += 1
            role = classify_shape(shape)

            if role == "table":
                table_count += 1
                tblocks = extract_table_blocks(shape, uid, start_order=block_counter + 1)
                block_counter += len(tblocks)
                text_shape_count += 1 if tblocks else 0
                blocks.extend(tblocks)
            elif shape.has_text_frame:
                text_shape_count += 1
                tblocks = extract_text_blocks(shape, uid, role, start_order=block_counter + 1)
                block_counter += len(tblocks)
                blocks.extend(tblocks)

        raw_text = " ".join(b.text for b in blocks)

        # Title detection
        title = ""
        title_source = "fallback"
        if detect_titles:
            title, title_source = detect_title(slide, blocks)
        if not title:
            title = f"Slide {slide_idx}"
            title_source = "fallback"

        # Notes
        notes_present = False
        notes_text = ""
        if include_notes:
            notes_text = extract_notes(slide)
            notes_present = bool(notes_text.strip())

        record = SlideRecord(
            source_file=source_name,
            source_file_index=file_index,
            slide_number=slide_idx,
            slide_uid=uid,
            title=title,
            title_source=title_source,  # type: ignore[arg-type]
            notes_present=notes_present,
            notes_text=notes_text,
            raw_text_char_count=len(raw_text),
            shape_count=shape_count,
            text_shape_count=text_shape_count,
            table_count=table_count,
            text_blocks=blocks,
        )
        records.append(record)
        logger.debug("  -> %d blocks, %d chars", len(blocks), len(raw_text))

    logger.info("Extracted %d slides from %s", len(records), source_name)
    return records
