"""Skill registry for SlideBridge.

Each skill is a callable dataclass with a ``description`` class attribute and
a ``run()`` method.  Skills delegate to the existing stage modules so that
orchestration code only needs to reference skill names.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from slidebridge.models.manifest import RunManifest
from slidebridge.models.slide import SlideRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skill dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PptxTextExtractionSkill:
    """Extract structured text from PPTX shapes, tables, and notes."""

    description: str = "Extract structured text from PPTX shapes, tables, and notes"

    def run(
        self,
        pptx_path: Path,
        file_index: int,
        include_notes: bool = False,
    ) -> list[SlideRecord]:
        """Extract all slides from *pptx_path* and return SlideRecord objects.

        Parameters
        ----------
        pptx_path:
            Path to the source PPTX file.
        file_index:
            1-based index of this deck within a multi-file run.
        include_notes:
            When True, speaker notes are extracted into each SlideRecord.
        """
        from slidebridge.extract.pptx_reader import extract_deck

        logger.info(
            "PptxTextExtractionSkill: extracting %s (file_index=%d, notes=%s)",
            pptx_path.name,
            file_index,
            include_notes,
        )
        return extract_deck(pptx_path, file_index=file_index, include_notes=include_notes)


@dataclass
class SlideRenderingSkill:
    """Convert PPTX to PDF via LibreOffice, then render PDF pages to PNG."""

    description: str = "Convert PPTX to PDF via LibreOffice, then render PDF pages to PNG"

    def run(
        self,
        pptx_path: Path,
        pdf_dir: Path,
        img_dir: Path,
        dpi: int = 180,
    ) -> list[Path]:
        """Render *pptx_path* to per-slide PNG images.

        Parameters
        ----------
        pptx_path:
            Source PPTX file to render.
        pdf_dir:
            Directory where the intermediate PDF will be placed.
        img_dir:
            Root directory under which a per-deck sub-folder will be created
            containing the PNG images.
        dpi:
            Resolution for PNG rendering (default 180).

        Returns the list of generated image paths in slide order.
        """
        from slidebridge.render.libreoffice import convert_to_pdf
        from slidebridge.render.pdf_renderer import render_pdf_to_images

        logger.info("SlideRenderingSkill: rendering %s at %d DPI", pptx_path.name, dpi)
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = convert_to_pdf(pptx_path, out_dir=pdf_dir)

        deck_img_dir = img_dir / pptx_path.stem
        deck_img_dir.mkdir(parents=True, exist_ok=True)
        images = render_pdf_to_images(pdf_path, out_dir=deck_img_dir, dpi=dpi, fmt="png")
        logger.info("SlideRenderingSkill: %d images -> %s", len(images), deck_img_dir)
        return images


@dataclass
class ReadingOrderReconciliationSkill:
    """Reorder text blocks, score confidence, and flag suspicious slides."""

    description: str = "Reorder text blocks, score confidence, and flag suspicious slides"

    def run(
        self,
        slides: list[SlideRecord],
        img_dir: Path | None = None,
    ) -> list[SlideRecord]:
        """Apply reading-order, confidence scoring, and warning flags.

        Parameters
        ----------
        slides:
            Raw SlideRecord objects from the extraction stage.
        img_dir:
            When supplied, image_path is resolved for each slide under this
            directory using the standard ``<deck_stem>/slide_NNN.png`` layout.

        Returns the updated list of SlideRecord objects.
        """
        from slidebridge.constants import SLIDE_IMAGE_STEM
        from slidebridge.reconcile.confidence import score_slide
        from slidebridge.reconcile.reading_order import reorder_slide
        from slidebridge.reconcile.warnings import flag_slide

        logger.info(
            "ReadingOrderReconciliationSkill: reconciling %d slides", len(slides)
        )
        processed: list[SlideRecord] = []
        for slide in slides:
            slide = reorder_slide(slide, merge_fragments=True)
            slide = score_slide(slide)
            slide = flag_slide(slide, warn_low_confidence=True)
            if img_dir and not slide.image_path:
                deck_stem = Path(slide.source_file).stem
                img_path = (
                    img_dir
                    / deck_stem
                    / f"{SLIDE_IMAGE_STEM.format(slide.slide_number)}.png"
                )
                if img_path.exists():
                    slide = slide.model_copy(update={"image_path": str(img_path)})
            processed.append(slide)
        return processed


@dataclass
class DocxReviewPackAssemblySkill:
    """Assemble an A4 DOCX review pack from a manifest."""

    description: str = "Assemble an A4 DOCX review pack from a manifest"

    def run(
        self,
        manifest: RunManifest,
        images_root: Path,
        out_path: Path,
    ) -> None:
        """Write the DOCX review pack to *out_path*.

        Parameters
        ----------
        manifest:
            Fully reconciled RunManifest containing all slide records.
        images_root:
            Root directory where per-deck image sub-folders are located.
        out_path:
            Destination path for the output DOCX file.
        """
        from slidebridge.build.docx_builder import build_review_pack

        logger.info(
            "DocxReviewPackAssemblySkill: building DOCX -> %s (%d slides)",
            out_path,
            len(manifest.slides),
        )
        build_review_pack(
            manifest,
            images_root=images_root,
            out_path=out_path,
            page_size="A4",
            margins="narrow",
        )


@dataclass
class ArtifactAuditSkill:
    """Validate counts, write slides.csv, warnings.csv, run_report.json."""

    description: str = "Validate counts, write slides.csv, warnings.csv, run_report.json"

    def run(
        self,
        manifest: RunManifest,
        out_dir: Path,
    ) -> dict[str, Path]:
        """Write audit artefacts and return a mapping of name -> path.

        Parameters
        ----------
        manifest:
            The RunManifest to audit.
        out_dir:
            Directory where audit files will be written.

        Returns a dict with keys ``slides_csv``, ``warnings_csv``, and
        ``run_report`` mapping to the respective output paths.
        """
        from slidebridge.audit.csv_writer import write_audit_csvs
        from slidebridge.audit.report_writer import write_run_report
        from slidebridge.constants import (
            SLIDES_CSV_FILENAME,
            WARNINGS_CSV_FILENAME,
        )

        logger.info(
            "ArtifactAuditSkill: writing audit artefacts -> %s", out_dir
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        if manifest.summary is None:
            manifest.compute_summary()

        write_audit_csvs(manifest, out_dir=out_dir)
        report_path = write_run_report(manifest, out_dir=out_dir)

        return {
            "slides_csv": out_dir / SLIDES_CSV_FILENAME,
            "warnings_csv": out_dir / WARNINGS_CSV_FILENAME,
            "run_report": report_path,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SkillRegistry: dict[str, object] = {
    "pptx_text_extraction": PptxTextExtractionSkill(),
    "slide_rendering": SlideRenderingSkill(),
    "reading_order_reconciliation": ReadingOrderReconciliationSkill(),
    "docx_review_pack_assembly": DocxReviewPackAssemblySkill(),
    "artifact_audit": ArtifactAuditSkill(),
}


def get_skill(name: str) -> object:
    """Return the skill instance registered under *name*.

    Raises
    ------
    KeyError
        If *name* is not present in the registry.
    """
    if name not in SkillRegistry:
        available = ", ".join(SkillRegistry.keys())
        raise KeyError(
            f"Unknown skill {name!r}. Available skills: {available}"
        )
    return SkillRegistry[name]
