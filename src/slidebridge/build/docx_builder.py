"""Assemble the A4 DOCX review pack from a RunManifest."""

from __future__ import annotations

import logging
from pathlib import Path

from docx import Document

from slidebridge.build.docx_images import add_slide_image
from slidebridge.build.docx_styles import apply_page_layout
from slidebridge.build.docx_tables import add_text_table
from slidebridge.build.headings import add_slide_heading
from slidebridge.models.manifest import RunManifest
from slidebridge.models.slide import SlideRecord

logger = logging.getLogger(__name__)

_WARNING_TEXT = (
    "Extraction warning: this slide may contain visually present text "
    "not fully captured by structured extraction. Review against screenshot."
)


def build_review_pack(
    manifest: RunManifest,
    images_root: Path,
    out_path: Path,
    page_size: str = "A4",
    margins: str = "narrow",
) -> None:
    """Write the DOCX review pack to out_path."""
    doc = Document()
    apply_page_layout(doc, page_size=page_size, margins=margins)

    total = len(manifest.slides)
    for idx, slide in enumerate(manifest.slides, start=1):
        logger.debug("Building slide %d/%d: %s", idx, total, slide.slide_uid)
        _add_slide_section(doc, slide, images_root)
        # Page break between slides (not after the last one)
        if idx < total:
            doc.add_page_break()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    logger.info("Saved DOCX -> %s (%d slides)", out_path, total)


def _add_slide_section(doc: Document, slide: SlideRecord, images_root: Path) -> None:
    # 1. Heading
    add_slide_heading(doc, slide)

    # 2. Metadata line
    meta = (
        f"Source: {slide.source_file} | "
        f"Slide: {slide.slide_number} | "
        f"Confidence: {slide.confidence:.2f} | "
        f"Warnings: {len(slide.warnings)}"
    )
    p = doc.add_paragraph(meta)
    p.style = doc.styles["Normal"]

    # 3. Screenshot
    img_path = _resolve_image(slide, images_root)
    if img_path and img_path.exists():
        add_slide_image(doc, img_path)
    else:
        doc.add_paragraph(f"[Image not found: {slide.image_path}]")
        logger.warning("Image missing for slide %s: %s", slide.slide_uid, slide.image_path)

    # 4. Warning block
    if slide.warnings:
        wp = doc.add_paragraph(_WARNING_TEXT)
        wp.runs[0].bold = True

    # 5. Editable table
    add_text_table(doc, slide)


def _resolve_image(slide: SlideRecord, images_root: Path) -> Path | None:
    """Find the slide image under images_root."""
    if slide.image_path:
        p = Path(slide.image_path)
        if p.exists():
            return p
    # Fallback: look under images_root / deck_stem / slide_NNN.png
    from slidebridge.constants import SLIDE_IMAGE_STEM
    stem = Path(slide.source_file).stem
    candidate = images_root / stem / f"{SLIDE_IMAGE_STEM.format(slide.slide_number)}.png"
    return candidate
