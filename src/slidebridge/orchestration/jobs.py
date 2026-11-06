"""Individual command implementations called by cli.py.

Each cmd_* function is a thin dispatcher that coordinates stage modules.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import orjson
from rich.console import Console
from rich.table import Table

from slidebridge.models.manifest import RunManifest

logger = logging.getLogger(__name__)
console = Console()


def cmd_init() -> None:
    """Create project scaffolding and a sample slidebridge.yaml."""
    sample_yaml = Path("slidebridge.yaml")
    if sample_yaml.exists():
        console.print("[yellow]slidebridge.yaml already exists — skipping.[/yellow]")
    else:
        import yaml

        from slidebridge.config import SlideBridgeConfig
        cfg = SlideBridgeConfig()
        sample_yaml.write_text(
            yaml.dump(cfg.model_dump(), default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        console.print(f"[green]Created {sample_yaml}[/green]")
    for d in ("input", "work/pdf", "work/images", "work/json", "work/reconciled",
              "work/logs", "output"):
        Path(d).mkdir(parents=True, exist_ok=True)
    console.print("[green]Project directories ready.[/green]")


def cmd_inspect(input_files: list[Path]) -> None:
    """Print a summary table of each PPTX deck without processing."""
    from pptx import Presentation

    table = Table(title="Deck Inspection", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Slides", justify="right")
    table.add_column("Has Notes")

    for path in input_files:
        try:
            prs = Presentation(str(path))
            slide_count = len(prs.slides)
            has_notes = any(
                slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip()
                for slide in prs.slides
            )
            table.add_row(path.name, str(slide_count), "Yes" if has_notes else "No")
        except Exception as exc:
            table.add_row(path.name, "ERROR", str(exc))
            logger.error("Failed to inspect %s: %s", path, exc)

    console.print(table)


def cmd_extract(
    input_files: list[Path],
    out: Path,
    include_notes: bool,
    detect_titles: bool,
    pretty: bool,
) -> list[Path]:
    """Extract slide content from PPTX files to JSON. Returns list of JSON paths."""
    from slidebridge.extract.pptx_reader import extract_deck

    out.mkdir(parents=True, exist_ok=True)
    json_paths: list[Path] = []

    for idx, pptx_path in enumerate(input_files, start=1):
        logger.info("Extracting %s (%d/%d)", pptx_path.name, idx, len(input_files))
        slides = extract_deck(
            pptx_path,
            file_index=idx,
            include_notes=include_notes,
            detect_titles=detect_titles,
        )
        json_path = out / f"{pptx_path.stem}.json"
        option = orjson.OPT_INDENT_2 if pretty else None
        data = [s.model_dump() for s in slides]
        json_path.write_bytes(orjson.dumps(data, option=option))
        logger.info("Wrote %s (%d slides)", json_path, len(slides))
        json_paths.append(json_path)

    return json_paths


def cmd_render(
    input_files: list[Path],
    pdf_dir: Path,
    img_dir: Path,
    dpi: int,
    fmt: str,
) -> None:
    """Convert PPTX → PDF → PNG for each deck."""
    from slidebridge.render.libreoffice import convert_to_pdf
    from slidebridge.render.pdf_renderer import render_pdf_to_images

    pdf_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    for pptx_path in input_files:
        logger.info("Rendering %s", pptx_path.name)
        pdf_path = convert_to_pdf(pptx_path, out_dir=pdf_dir)
        deck_img_dir = img_dir / pptx_path.stem
        deck_img_dir.mkdir(parents=True, exist_ok=True)
        render_pdf_to_images(pdf_path, out_dir=deck_img_dir, dpi=dpi, fmt=fmt)
        logger.info("Rendered images -> %s", deck_img_dir)


def cmd_reconcile(
    json_files: list[Path],
    out: Path,
    merge_fragments: bool,
    warn_low_confidence: bool,
    img_dir: Path | None = None,
    fmt: str = "png",
) -> Path:
    """Apply reading-order heuristics and confidence scoring; write manifest."""
    from slidebridge.constants import SLIDE_IMAGE_STEM
    from slidebridge.models.manifest import InputDeck
    from slidebridge.models.slide import SlideRecord
    from slidebridge.reconcile.confidence import score_slide
    from slidebridge.reconcile.reading_order import reorder_slide
    from slidebridge.reconcile.warnings import flag_slide

    out.mkdir(parents=True, exist_ok=True)

    all_slides: list[SlideRecord] = []
    input_decks: list[InputDeck] = []

    for json_path in json_files:
        raw = orjson.loads(json_path.read_bytes())
        slides = [SlideRecord.model_validate(s) for s in raw]

        # Bug fix 1: collect updated slides, not originals
        processed: list[SlideRecord] = []
        for slide in slides:
            slide = reorder_slide(slide, merge_fragments=merge_fragments)
            slide = score_slide(slide)
            slide = flag_slide(slide, warn_low_confidence=warn_low_confidence)
            # Bug fix 3: link image_path from render output
            if img_dir and not slide.image_path:
                deck_stem = Path(slide.source_file).stem
                img_path = img_dir / deck_stem / f"{SLIDE_IMAGE_STEM.format(slide.slide_number)}.{fmt}"
                if img_path.exists():
                    slide = slide.model_copy(update={"image_path": str(img_path)})
            processed.append(slide)

        all_slides.extend(processed)

        # Bug fix 2: build InputDeck entries so manifest.inputs is populated
        source_name = processed[0].source_file if processed else json_path.stem
        input_decks.append(InputDeck(
            source_file=source_name,
            slide_count=len(processed),
            image_dir=str(img_dir / Path(source_name).stem) if img_dir else "",
        ))

    manifest = RunManifest(slides=all_slides, inputs=input_decks)
    manifest.compute_summary()
    manifest_path = out / "manifest.json"
    manifest_path.write_bytes(orjson.dumps(manifest.model_dump(), option=orjson.OPT_INDENT_2))
    logger.info("Wrote manifest -> %s (%d slides)", manifest_path, len(all_slides))
    return manifest_path


def cmd_build_docx(
    manifest: Path,
    images: Path,
    out: Path,
    page_size: str,
    margins: str,
) -> None:
    """Build the DOCX review pack from a reconciled manifest."""
    from slidebridge.build.docx_builder import build_review_pack

    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_obj = RunManifest.model_validate(orjson.loads(manifest.read_bytes()))
    build_review_pack(manifest_obj, images_root=images, out_path=out,
                      page_size=page_size, margins=margins)
    console.print(f"[green]DOCX written -> {out}[/green]")


def cmd_audit(manifest: Path, out: Path) -> None:
    """Write slides.csv, warnings.csv, and run_report.json."""
    from slidebridge.audit.csv_writer import write_audit_csvs
    from slidebridge.audit.report_writer import write_run_report

    out.mkdir(parents=True, exist_ok=True)
    manifest_obj = RunManifest.model_validate(orjson.loads(manifest.read_bytes()))
    write_audit_csvs(manifest_obj, out_dir=out)
    write_run_report(manifest_obj, out_dir=out)
    console.print(f"[green]Audit files written -> {out}[/green]")


def cmd_validate(manifest: Path) -> bool:
    """Validate manifest.json against the JSON schema. Returns True if valid."""
    from slidebridge.integrations.schema_validator import validate_manifest

    ok, errors = validate_manifest(manifest)
    if ok:
        console.print("[green]Manifest is valid.[/green]")
    else:
        console.print("[red]Manifest validation failed:[/red]")
        for err in errors:
            console.print(f"  [red]{err}[/red]")
    return ok


def cmd_clean(workdir: Path) -> None:
    """Remove intermediate work artifacts."""
    for subdir in ("pdf", "images", "json", "reconciled"):
        target = workdir / subdir
        if target.exists():
            shutil.rmtree(target)
            logger.info("Removed %s", target)
    console.print(f"[green]Cleaned {workdir}[/green]")


def cmd_align(
    review_pack: Path,
    edited_doc: Path,
    out: Path,
) -> None:
    """Populate Edited Text in a review pack by aligning against an edited DOCX."""
    from slidebridge.align.pipeline import run_alignment

    stats = run_alignment(review_pack, edited_doc, out)

    # Summary table
    from rich.table import Table as RichTable
    tbl = RichTable(title="Alignment Summary", show_lines=True)
    tbl.add_column("Change Type")
    tbl.add_column("Count", justify="right")
    for ct, count in sorted(stats.by_change_type.items()):
        colour = "red" if ct == "Not Found" else "green" if ct == "Unchanged" else "yellow"
        tbl.add_row(f"[{colour}]{ct}[/{colour}]", str(count))
    tbl.add_row("[bold]Total[/bold]", str(stats.total))
    console.print(tbl)
    console.print(f"[green]Aligned DOCX written -> {out}[/green]")
