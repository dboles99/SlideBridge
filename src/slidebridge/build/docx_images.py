"""Insert a slide screenshot into a DOCX document."""

from __future__ import annotations

import logging
from pathlib import Path

from docx import Document
from docx.shared import Inches

from slidebridge.constants import IMAGE_WIDTH_INCHES
from slidebridge.render.image_optimizer import resize_for_docx

logger = logging.getLogger(__name__)


def add_slide_image(
    doc: Document,
    img_path: Path,
    width_inches: float = IMAGE_WIDTH_INCHES,
    optimize: bool = True,
) -> None:
    """Insert the slide screenshot, resizing if needed to avoid DOCX bloat."""
    display_path = img_path
    if optimize:
        try:
            display_path = resize_for_docx(img_path)
        except Exception as exc:
            logger.warning("Image resize failed for %s: %s — inserting original", img_path, exc)
            display_path = img_path

    try:
        doc.add_picture(str(display_path), width=Inches(width_inches))
        # Center the image paragraph
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        last_para = doc.paragraphs[-1]
        last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception as exc:
        logger.error("Failed to insert image %s: %s", display_path, exc)
        doc.add_paragraph(f"[Image insert failed: {display_path.name}]")
