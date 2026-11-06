"""Integration tests for the extract → reconcile → build-docx pipeline.

These tests exercise the full pipeline (minus render, which requires LibreOffice)
against two synthetic PPTX decks built in code (see tests/synthetic_decks.py).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import orjson
import pytest

from slidebridge.integrations.schema_validator import validate_manifest
from slidebridge.models.manifest import RunManifest
from slidebridge.orchestration.jobs import cmd_build_docx, cmd_extract, cmd_reconcile
from tests.synthetic_decks import PPTX_PART1, PPTX_PART2

# ---------------------------------------------------------------------------
# Synthetic decks
# ---------------------------------------------------------------------------


_BOTH_PRESENT = PPTX_PART1.exists() and PPTX_PART2.exists()
_SKIP_REASON = "Synthetic PPTX decks not present"

EXPECTED_SLIDES_EACH = 17
EXPECTED_TOTAL_SLIDES = 34  # 17 + 17


# ---------------------------------------------------------------------------
# Helper: default cmd_extract kwargs so tests aren't verbose
# ---------------------------------------------------------------------------

def _extract(input_files: list[Path], out: Path) -> list[Path]:
    return cmd_extract(
        input_files=input_files,
        out=out,
        include_notes=True,
        detect_titles=True,
        pretty=True,
    )


def _reconcile(json_files: list[Path], out: Path) -> Path:
    return cmd_reconcile(
        json_files=json_files,
        out=out,
        merge_fragments=False,
        warn_low_confidence=True,
        img_dir=None,
    )


# ---------------------------------------------------------------------------
# test 1 — extract both decks
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BOTH_PRESENT, reason=_SKIP_REASON)
def test_extract_both_decks():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "json"

        json_paths = _extract([PPTX_PART1, PPTX_PART2], out)

        assert len(json_paths) == 2, "Expected one JSON file per deck"

        for pptx, json_path in zip([PPTX_PART1, PPTX_PART2], json_paths):
            assert json_path.exists(), f"JSON not written for {pptx.name}"

            slides = orjson.loads(json_path.read_bytes())
            assert len(slides) == EXPECTED_SLIDES_EACH, (
                f"{pptx.name}: expected {EXPECTED_SLIDES_EACH} slides, got {len(slides)}"
            )

            for slide in slides:
                assert slide.get("title"), (
                    f"Slide {slide.get('slide_number')} in {pptx.name} has no title"
                )
                assert slide.get("slide_uid"), (
                    f"Slide {slide.get('slide_number')} in {pptx.name} has no slide_uid"
                )


# ---------------------------------------------------------------------------
# test 2 — reconcile two decks
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BOTH_PRESENT, reason=_SKIP_REASON)
def test_reconcile_two_decks():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        json_dir = tmp_path / "json"
        reconcile_dir = tmp_path / "reconciled"

        json_paths = _extract([PPTX_PART1, PPTX_PART2], json_dir)
        manifest_path = _reconcile(json_paths, reconcile_dir)

        assert manifest_path.exists(), "manifest.json was not written"
        assert manifest_path.name == "manifest.json"

        manifest_obj = RunManifest.model_validate(orjson.loads(manifest_path.read_bytes()))

        assert len(manifest_obj.slides) == EXPECTED_TOTAL_SLIDES, (
            f"Expected {EXPECTED_TOTAL_SLIDES} slides in manifest, got {len(manifest_obj.slides)}"
        )

        ok, errors = validate_manifest(manifest_path)
        assert ok, f"Manifest failed schema validation: {errors}"

        assert manifest_obj.summary is not None, "RunSummary was not computed"
        assert manifest_obj.summary.total_files == 2, (
            f"Expected total_files=2, got {manifest_obj.summary.total_files}"
        )
        assert manifest_obj.summary.total_slides == EXPECTED_TOTAL_SLIDES, (
            f"Expected total_slides={EXPECTED_TOTAL_SLIDES}, "
            f"got {manifest_obj.summary.total_slides}"
        )


# ---------------------------------------------------------------------------
# test 3 — build DOCX from manifest
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BOTH_PRESENT, reason=_SKIP_REASON)
def test_build_docx_from_manifest():
    from docx import Document

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        json_dir = tmp_path / "json"
        reconcile_dir = tmp_path / "reconciled"
        docx_path = tmp_path / "output" / "review_pack.docx"

        json_paths = _extract([PPTX_PART1, PPTX_PART2], json_dir)
        manifest_path = _reconcile(json_paths, reconcile_dir)

        cmd_build_docx(
            manifest=manifest_path,
            images=tmp_path / "images",   # empty — image inserts will fail gracefully
            out=docx_path,
            page_size="A4",
            margins="narrow",
        )

        assert docx_path.exists(), "Output DOCX file was not created"

        doc = Document(str(docx_path))

        # One Heading 1 per slide
        heading_paras = [p for p in doc.paragraphs if p.style.name == "Heading 1"]
        assert len(heading_paras) == EXPECTED_TOTAL_SLIDES, (
            f"Expected {EXPECTED_TOTAL_SLIDES} Heading 1 paragraphs, "
            f"got {len(heading_paras)}"
        )

        # Total paragraphs must exceed heading count (metadata lines, image
        # placeholders, warning blocks, and table cell content are all paragraphs)
        assert len(doc.paragraphs) > EXPECTED_TOTAL_SLIDES, (
            "Paragraph count should exceed slide heading count"
        )

        # One table per slide
        assert len(doc.tables) == EXPECTED_TOTAL_SLIDES, (
            f"Expected {EXPECTED_TOTAL_SLIDES} tables, got {len(doc.tables)}"
        )


# ---------------------------------------------------------------------------
# test 4 — full pipeline chained in one test
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BOTH_PRESENT, reason=_SKIP_REASON)
def test_full_extract_to_docx_pipeline():
    from docx import Document

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Stage 1: extract
        json_paths = _extract([PPTX_PART1, PPTX_PART2], tmp_path / "json")
        assert len(json_paths) == 2

        # Stage 2: reconcile
        manifest_path = _reconcile(json_paths, tmp_path / "reconciled")
        assert manifest_path.exists()

        # Stage 3: build DOCX
        docx_path = tmp_path / "output" / "review_pack.docx"
        cmd_build_docx(
            manifest=manifest_path,
            images=tmp_path / "images",
            out=docx_path,
            page_size="A4",
            margins="narrow",
        )
        assert docx_path.exists()

        # Quick sanity check on the produced document
        doc = Document(str(docx_path))
        heading_count = sum(1 for p in doc.paragraphs if p.style.name == "Heading 1")
        assert heading_count == EXPECTED_TOTAL_SLIDES
        assert len(doc.tables) == EXPECTED_TOTAL_SLIDES


# ---------------------------------------------------------------------------
# test 5 — slide UIDs are globally unique across both decks
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BOTH_PRESENT, reason=_SKIP_REASON)
def test_slide_uids_unique():
    with tempfile.TemporaryDirectory() as tmp:
        json_paths = _extract([PPTX_PART1, PPTX_PART2], Path(tmp) / "json")

        all_uids: list[str] = []
        for json_path in json_paths:
            slides = orjson.loads(json_path.read_bytes())
            all_uids.extend(s["slide_uid"] for s in slides)

        assert len(all_uids) == EXPECTED_TOTAL_SLIDES
        assert len(set(all_uids)) == EXPECTED_TOTAL_SLIDES, (
            f"Duplicate slide_uids found: "
            f"{[u for u in all_uids if all_uids.count(u) > 1]}"
        )


# ---------------------------------------------------------------------------
# test 6 — manifest slide order: Part 1 slides first, then Part 2
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BOTH_PRESENT, reason=_SKIP_REASON)
def test_manifest_slide_order():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        json_paths = _extract([PPTX_PART1, PPTX_PART2], tmp_path / "json")
        manifest_path = _reconcile(json_paths, tmp_path / "reconciled")

        manifest_obj = RunManifest.model_validate(orjson.loads(manifest_path.read_bytes()))
        slides = manifest_obj.slides

        assert len(slides) == EXPECTED_TOTAL_SLIDES

        part1_slides = slides[:EXPECTED_SLIDES_EACH]
        part2_slides = slides[EXPECTED_SLIDES_EACH:]

        # All first 17 come from Part 1
        for slide in part1_slides:
            assert PPTX_PART1.name in slide.source_file or PPTX_PART1.stem in slide.source_file, (
                f"Expected Part 1 source, got: {slide.source_file}"
            )

        # All last 17 come from Part 2
        for slide in part2_slides:
            assert PPTX_PART2.name in slide.source_file or PPTX_PART2.stem in slide.source_file, (
                f"Expected Part 2 source, got: {slide.source_file}"
            )

        # Slide numbers within each block are in ascending order
        part1_nums = [s.slide_number for s in part1_slides]
        part2_nums = [s.slide_number for s in part2_slides]
        assert part1_nums == sorted(part1_nums), "Part 1 slides not in slide_number order"
        assert part2_nums == sorted(part2_nums), "Part 2 slides not in slide_number order"
