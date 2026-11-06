"""Render PDF pages to PNG images using PyMuPDF.

Each page becomes one PNG file named slide_001.png, slide_002.png, etc.
Validates that the output image count matches the PDF page count.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

from slidebridge.constants import SLIDE_IMAGE_STEM

logger = logging.getLogger(__name__)


def render_pdf_to_images(
    pdf_path: Path,
    out_dir: Path,
    dpi: int = 180,
    fmt: str = "png",
) -> list[Path]:
    """Render every page of a PDF to an image file.

    Returns the list of generated image paths in page order.
    Raises RuntimeError on count mismatch or zero-byte files.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    if page_count == 0:
        raise RuntimeError(f"PDF has no pages: {pdf_path}")

    zoom = dpi / 72.0  # PyMuPDF default is 72 DPI
    mat = fitz.Matrix(zoom, zoom)

    image_paths: list[Path] = []

    for page_num in range(page_count):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        stem = SLIDE_IMAGE_STEM.format(page_num + 1)
        img_path = out_dir / f"{stem}.{fmt}"
        pix.save(str(img_path))

        if img_path.stat().st_size == 0:
            raise RuntimeError(f"Zero-byte image generated: {img_path}")

        image_paths.append(img_path)
        logger.debug("  Rendered page %d -> %s", page_num + 1, img_path.name)

    doc.close()

    # Validation
    if len(image_paths) != page_count:
        raise RuntimeError(
            f"Image count mismatch for {pdf_path.name}: "
            f"expected {page_count}, got {len(image_paths)}"
        )

    logger.info(
        "Rendered %d pages from %s -> %s (DPI=%d)",
        page_count, pdf_path.name, out_dir, dpi,
    )
    return image_paths
