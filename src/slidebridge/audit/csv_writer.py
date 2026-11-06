"""Write slides.csv and warnings.csv audit files."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from slidebridge.constants import SLIDES_CSV_FILENAME, WARNINGS_CSV_FILENAME
from slidebridge.models.audit import AuditRow
from slidebridge.models.manifest import RunManifest
from slidebridge.models.slide import SlideRecord

logger = logging.getLogger(__name__)


def write_audit_csvs(manifest: RunManifest, out_dir: Path) -> None:
    """Write slides.csv and warnings.csv to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [_make_row(s) for s in manifest.slides]

    _write_slides_csv(rows, out_dir / SLIDES_CSV_FILENAME)
    _write_warnings_csv(rows, out_dir / WARNINGS_CSV_FILENAME)


def _make_row(slide: SlideRecord) -> AuditRow:
    return AuditRow(
        source_file=slide.source_file,
        slide_number=slide.slide_number,
        title=slide.title,
        image_exists=bool(slide.image_path),
        text_shape_count=slide.text_shape_count,
        raw_text_char_count=slide.raw_text_char_count,
        confidence=slide.confidence,
        warning_count=len(slide.warnings),
        warnings="; ".join(slide.warnings),
    )


def _write_slides_csv(rows: list[AuditRow], path: Path) -> None:
    fieldnames = list(AuditRow.model_fields.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump())
    logger.info("Wrote %s (%d rows)", path, len(rows))


def _write_warnings_csv(rows: list[AuditRow], path: Path) -> None:
    warning_rows = [r for r in rows if r.warning_count > 0]
    fieldnames = ["source_file", "slide_number", "title", "confidence", "warnings"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in warning_rows:
            writer.writerow({k: getattr(row, k) for k in fieldnames})
    logger.info("Wrote %s (%d warning rows)", path, len(warning_rows))
