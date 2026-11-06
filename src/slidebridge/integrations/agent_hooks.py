"""Agent hooks called by an orchestrator at each pipeline stage boundary.

Each hook logs what happened and may raise ``RuntimeError`` to abort the
pipeline when a validation check fails.
"""

from __future__ import annotations

import logging
from pathlib import Path

from slidebridge.models.manifest import RunManifest
from slidebridge.models.slide import SlideRecord

logger = logging.getLogger(__name__)


def on_extract_complete(slides: list[SlideRecord], source_file: str) -> None:
    """Called after the extract stage finishes for one deck.

    Logs a summary of the extracted slides.  No abort condition is applied
    here — zero slides is unusual but handled downstream.

    Parameters
    ----------
    slides:
        The SlideRecord objects produced for *source_file*.
    source_file:
        The name (or path) of the source PPTX deck.
    """
    logger.info(
        "[hook] on_extract_complete: %s — %d slides extracted",
        source_file,
        len(slides),
    )
    if not slides:
        logger.warning(
            "[hook] on_extract_complete: no slides extracted from %s", source_file
        )


def on_render_complete(img_dir: Path, expected_count: int) -> None:
    """Called after the render stage finishes for one deck.

    Delegates count validation to ``validate_render_output`` from
    ``render.render_manifest``.  Raises ``RuntimeError`` if any images are
    missing or zero-byte.

    Parameters
    ----------
    img_dir:
        The directory that contains the rendered images for a single deck
        (i.e. the per-deck sub-folder, not the root images dir).
    expected_count:
        Number of slides expected — must equal the number of image files.
    """
    from slidebridge.render.render_manifest import validate_render_output

    # img_dir is the per-deck folder: <root>/images/<deck_stem>/
    # validate_render_output expects (img_dir_root, deck_stem, expected_count)
    deck_stem = img_dir.name
    img_root = img_dir.parent

    logger.info(
        "[hook] on_render_complete: validating %d images in %s",
        expected_count,
        img_dir,
    )
    errors = validate_render_output(img_root, deck_stem, expected_count)
    if errors:
        msg = (
            f"Render validation failed for deck '{deck_stem}' "
            f"({len(errors)} error(s)):\n" + "\n".join(f"  {e}" for e in errors)
        )
        logger.error("[hook] on_render_complete: %s", msg)
        raise RuntimeError(msg)

    logger.info(
        "[hook] on_render_complete: all %d images present for '%s'",
        expected_count,
        deck_stem,
    )


def on_reconcile_complete(manifest: RunManifest) -> None:
    """Called after the reconcile stage writes the manifest.

    Serialises the manifest to a temporary bytes buffer and validates it via
    ``schema_validator.validate_manifest``.  Raises ``RuntimeError`` on
    validation failure.

    Parameters
    ----------
    manifest:
        The in-memory RunManifest produced by the reconcile stage.
    """
    import tempfile

    import orjson

    from slidebridge.integrations.schema_validator import validate_manifest

    logger.info(
        "[hook] on_reconcile_complete: validating manifest (%d slides)",
        len(manifest.slides),
    )

    # Write to a temp file so we can pass a Path to validate_manifest
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(
            orjson.dumps(manifest.model_dump(), option=orjson.OPT_INDENT_2)
        )

    try:
        ok, errors = validate_manifest(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not ok:
        msg = (
            "Manifest schema validation failed after reconcile "
            f"({len(errors)} error(s)):\n" + "\n".join(f"  {e}" for e in errors)
        )
        logger.error("[hook] on_reconcile_complete: %s", msg)
        raise RuntimeError(msg)

    logger.info("[hook] on_reconcile_complete: manifest is valid")


def on_build_complete(docx_path: Path, expected_slides: int) -> None:
    """Called after the build-docx stage writes the review pack.

    Opens the DOCX with python-docx and counts Heading 1 paragraphs.
    Raises ``RuntimeError`` if the count does not match *expected_slides*.

    Parameters
    ----------
    docx_path:
        Path to the written DOCX review pack.
    expected_slides:
        Number of slides that should correspond to Heading 1 entries.
    """
    from docx import Document

    logger.info(
        "[hook] on_build_complete: checking heading count in %s (expected %d)",
        docx_path,
        expected_slides,
    )

    if not docx_path.exists():
        raise RuntimeError(
            f"[hook] on_build_complete: DOCX not found at {docx_path}"
        )

    doc = Document(str(docx_path))
    heading1_count = sum(
        1 for p in doc.paragraphs
        if p.style is not None and p.style.name == "Heading 1"
    )

    if heading1_count != expected_slides:
        msg = (
            f"DOCX heading count mismatch: expected {expected_slides} "
            f"Heading 1 paragraphs, found {heading1_count} in {docx_path.name}"
        )
        logger.error("[hook] on_build_complete: %s", msg)
        raise RuntimeError(msg)

    logger.info(
        "[hook] on_build_complete: %d Heading 1 paragraphs — OK", heading1_count
    )


def on_audit_complete(audit_dir: Path) -> None:
    """Called after the audit stage writes its artefacts.

    Checks that ``slides.csv``, ``warnings.csv``, and ``run_report.json``
    all exist in *audit_dir*.  Raises ``RuntimeError`` listing any missing
    files.

    Parameters
    ----------
    audit_dir:
        Directory where the audit stage wrote its output files.
    """
    from slidebridge.constants import (
        RUN_REPORT_FILENAME,
        SLIDES_CSV_FILENAME,
        WARNINGS_CSV_FILENAME,
    )

    required = [SLIDES_CSV_FILENAME, WARNINGS_CSV_FILENAME, RUN_REPORT_FILENAME]
    missing = [f for f in required if not (audit_dir / f).exists()]

    logger.info(
        "[hook] on_audit_complete: checking artefacts in %s", audit_dir
    )

    if missing:
        msg = (
            f"Audit artefacts missing in {audit_dir}: "
            + ", ".join(missing)
        )
        logger.error("[hook] on_audit_complete: %s", msg)
        raise RuntimeError(msg)

    logger.info(
        "[hook] on_audit_complete: all audit artefacts present (%s)",
        ", ".join(required),
    )


def on_pipeline_error(stage: str, error: Exception) -> None:
    """Called when any pipeline stage raises an unhandled exception.

    Logs the error at ERROR level.  Does not re-raise; callers decide whether
    to abort.

    Parameters
    ----------
    stage:
        Name of the pipeline stage that failed (e.g. ``"render"``).
    error:
        The exception that was raised.
    """
    logger.error(
        "[hook] on_pipeline_error: stage '%s' failed — %s: %s",
        stage,
        type(error).__name__,
        error,
    )
