"""Resize images for DOCX insertion without bloating file size."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from slidebridge.constants import MAX_IMAGE_WIDTH_PX

logger = logging.getLogger(__name__)


def resize_for_docx(
    src: Path,
    max_width_px: int = MAX_IMAGE_WIDTH_PX,
) -> Path:
    """Return a resized copy of the image, or src if already within limits.

    The resized file is written alongside the original with a '_docx' suffix.
    Returns the path to use for DOCX insertion.
    """
    with Image.open(src) as img:
        w, h = img.size
        if w <= max_width_px:
            return src  # no resize needed

        scale = max_width_px / w
        new_h = int(h * scale)
        logger.debug("Resizing %s: %dx%d -> %dx%d", src.name, w, h, max_width_px, new_h)

        resized = img.resize((max_width_px, new_h), Image.Resampling.LANCZOS)
        out_path = src.with_stem(src.stem + "_docx")
        resized.save(str(out_path), optimize=True)
        return out_path
