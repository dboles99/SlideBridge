from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from pptx import Presentation

from slidebridge.render.render_manifest import validate_render_output
from tests.synthetic_decks import PPTX_PART1

pytestmark = pytest.mark.skipif(
    shutil.which("soffice") is None,
    reason="LibreOffice not on PATH",
)



def test_render_single_deck() -> None:
    """Render one synthetic deck and verify PDF + per-slide PNG output."""
    from slidebridge.orchestration.jobs import cmd_render

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pdf_dir = tmp_path / "pdf"
        img_dir = tmp_path / "images"

        cmd_render(
            input_files=[PPTX_PART1],
            pdf_dir=pdf_dir,
            img_dir=img_dir,
            dpi=96,
            fmt="png",
        )

        pdf_path = pdf_dir / f"{PPTX_PART1.stem}.pdf"
        deck_img_dir = img_dir / PPTX_PART1.stem

        assert pdf_path.exists(), f"Missing PDF output: {pdf_path}"
        assert deck_img_dir.exists(), f"Missing image directory: {deck_img_dir}"

        expected_count = len(Presentation(str(PPTX_PART1)).slides)
        errors = validate_render_output(img_dir, PPTX_PART1.stem, expected_count, fmt="png")
        assert not errors, f"Render output validation failed: {errors}"

        image_paths = sorted(deck_img_dir.glob("slide_*.png"))
        assert len(image_paths) == expected_count
        for image_path in image_paths:
            assert image_path.stat().st_size > 0, f"Zero-byte image: {image_path}"
