"""Build render manifest entries that link slides to their image paths."""

from __future__ import annotations

from pathlib import Path

from slidebridge.constants import SLIDE_IMAGE_STEM


def image_path_for_slide(
    img_dir: Path,
    deck_stem: str,
    slide_number: int,
    fmt: str = "png",
) -> Path:
    """Return the expected image path for a given slide number."""
    return img_dir / deck_stem / f"{SLIDE_IMAGE_STEM.format(slide_number)}.{fmt}"


def validate_render_output(
    img_dir: Path,
    deck_stem: str,
    expected_count: int,
    fmt: str = "png",
) -> list[str]:
    """Validate that all expected images exist and are non-empty.

    Returns a list of error strings (empty list = pass).
    """
    errors: list[str] = []
    for i in range(1, expected_count + 1):
        path = image_path_for_slide(img_dir, deck_stem, i, fmt)
        if not path.exists():
            errors.append(f"Missing image: {path}")
        elif path.stat().st_size == 0:
            errors.append(f"Zero-byte image: {path}")
    return errors
