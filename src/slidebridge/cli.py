"""SlideBridge CLI — entry point for all commands.

Commands
--------
init        Create project scaffolding and sample config
inspect     Print deck/slide summary without processing
extract     Extract slide content to JSON
render      Convert PPTX to PDF, then render slide PNGs
reconcile   Apply reading-order logic and confidence scoring
build-docx  Build the A4 DOCX review pack
audit       Write CSV and JSON audit files
run         One-shot full pipeline
validate    Validate manifests against JSON schema
clean       Remove work artifacts
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from slidebridge.config import load_config
from slidebridge.logging_setup import configure_logging

app = typer.Typer(
    name="slidebridge",
    help="Convert PPTX decks into review-oriented DOCX packages.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console()

# ── Common option types ────────────────────────────────────────────────────────

_InputFiles = Annotated[
    list[Path],
    typer.Argument(help="One or more .pptx files to process."),
]
_ConfigOpt = Annotated[
    Path | None,
    typer.Option("--config", "-c", help="Path to slidebridge.yaml config file."),
]
_VerboseOpt = Annotated[bool, typer.Option("--verbose", "-v", help="Enable DEBUG logging.")]
_DryRunOpt = Annotated[bool, typer.Option("--dry-run", help="Show what would run without doing it.")]


def _setup(config_path: Path | None, verbose: bool, workdir: Path | None = None) -> None:
    cfg = load_config(config_path)
    log_level = "DEBUG" if verbose else cfg.project.log_level
    log_dir = (workdir / "logs") if workdir else None
    configure_logging(log_level=log_level, log_dir=log_dir)


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command()
def init(
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Create project scaffolding and a sample slidebridge.yaml."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_init
    cmd_init()


@app.command()
def inspect(
    input_files: _InputFiles,
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Read PPTX files and print a deck/slide summary."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_inspect
    cmd_inspect(input_files)


@app.command()
def extract(
    input_files: _InputFiles,
    out: Annotated[Path, typer.Option(help="Output directory for JSON files.")] = Path("work/json"),
    include_notes: Annotated[bool, typer.Option(help="Extract speaker notes.")] = False,
    detect_titles: Annotated[bool, typer.Option(help="Auto-detect slide titles.")] = True,
    pretty: Annotated[bool, typer.Option(help="Pretty-print JSON output.")] = False,
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Extract slide content from PPTX files to JSON."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_extract
    cmd_extract(input_files, out=out, include_notes=include_notes,
                detect_titles=detect_titles, pretty=pretty)


@app.command()
def render(
    input_files: _InputFiles,
    pdf_dir: Annotated[Path, typer.Option(help="Directory for PDF files.")] = Path("work/pdf"),
    img_dir: Annotated[Path, typer.Option(help="Directory for PNG images.")] = Path("work/images"),
    dpi: Annotated[int, typer.Option(help="Render resolution in DPI.", min=72, max=600)] = 180,
    format: Annotated[str, typer.Option(help="Image format (png).")] = "png",
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Convert PPTX files to PDF, then render each slide as a PNG."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_render
    cmd_render(input_files, pdf_dir=pdf_dir, img_dir=img_dir, dpi=dpi, fmt=format)


@app.command()
def reconcile(
    json_files: Annotated[list[Path], typer.Argument(help="Extracted JSON files to process.")],
    out: Annotated[Path, typer.Option(help="Output directory for reconciled manifest.")] = Path("work/reconciled"),
    merge_fragments: Annotated[bool, typer.Option(help="Merge small adjacent text fragments.")] = True,
    warn_low_confidence: Annotated[bool, typer.Option(help="Flag low-confidence slides.")] = True,
    img_dir: Annotated[Path | None, typer.Option(help="Images root dir to link into slide records.")] = None,
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Apply reading-order logic and confidence scoring to extracted JSON."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_reconcile
    cmd_reconcile(json_files, out=out, merge_fragments=merge_fragments,
                  warn_low_confidence=warn_low_confidence, img_dir=img_dir)


@app.command(name="build-docx")
def build_docx(
    manifest: Annotated[Path, typer.Option(help="Path to reconciled manifest.json.")],
    images: Annotated[Path, typer.Option(help="Root directory containing slide images.")],
    out: Annotated[Path, typer.Option(help="Output .docx path.")] = Path("output/review_pack.docx"),
    page_size: Annotated[str, typer.Option(help="Page size (A4).")] = "A4",
    margins: Annotated[str, typer.Option(help="Margin preset (narrow).")] = "narrow",
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Build the A4 DOCX review pack from a reconciled manifest."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_build_docx
    cmd_build_docx(manifest=manifest, images=images, out=out,
                   page_size=page_size, margins=margins)


@app.command()
def audit(
    manifest: Annotated[Path, typer.Option(help="Path to reconciled manifest.json.")],
    out: Annotated[Path, typer.Option(help="Directory for audit files.")] = Path("output"),
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Write slides.csv, warnings.csv, and run_report.json audit files."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_audit
    cmd_audit(manifest=manifest, out=out)


@app.command()
def run(
    input_files: _InputFiles,
    workdir: Annotated[Path, typer.Option(help="Working directory for intermediate files.")] = Path("work"),
    out: Annotated[Path, typer.Option(help="Output .docx path.")] = Path("output/review_pack.docx"),
    page_size: Annotated[str, typer.Option(help="Page size (A4).")] = "A4",
    margins: Annotated[str, typer.Option(help="Margin preset (narrow).")] = "narrow",
    dpi: Annotated[int, typer.Option(help="Render DPI.", min=72, max=600)] = 180,
    include_notes: Annotated[bool, typer.Option(help="Include speaker notes.")] = False,
    resume: Annotated[bool, typer.Option(help="Skip already-rendered artifacts.")] = False,
    dry_run: _DryRunOpt = False,
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Run the full pipeline: extract -> render -> reconcile -> build-docx -> audit."""
    _setup(config, verbose, workdir=workdir)
    from slidebridge.models.run import RunOptions
    from slidebridge.orchestration.pipeline import run_pipeline

    opts = RunOptions(
        input_files=input_files,
        workdir=workdir,
        out=out,
        page_size=page_size,
        margins=margins,
        dpi=dpi,
        include_notes=include_notes,
        resume=resume,
        dry_run=dry_run,
        config_path=config,
    )
    success = run_pipeline(opts)
    if not success:
        raise typer.Exit(code=1)


@app.command()
def validate(
    manifest: Annotated[Path, typer.Argument(help="manifest.json to validate.")],
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Validate a manifest.json against the JSON schema."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_validate
    ok = cmd_validate(manifest)
    if not ok:
        raise typer.Exit(code=1)


@app.command()
def clean(
    workdir: Annotated[Path, typer.Option(help="Working directory to clean.")] = Path("work"),
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Remove intermediate work artifacts (pdf/, images/, json/, reconciled/)."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_clean
    cmd_clean(workdir)


@app.command()
def align(
    review_pack: Annotated[Path, typer.Argument(help="SlideBridge review-pack DOCX.")],
    edited_doc:  Annotated[Path, typer.Argument(help="Edited DOCX to align against.")],
    out: Annotated[Path, typer.Option(help="Output aligned DOCX path.")] = Path("output/aligned.docx"),
    config: _ConfigOpt = None,
    verbose: _VerboseOpt = False,
) -> None:
    """Populate Edited Text tables by aligning a review pack against an edited DOCX."""
    _setup(config, verbose)
    from slidebridge.orchestration.jobs import cmd_align
    cmd_align(review_pack=review_pack, edited_doc=edited_doc, out=out)


if __name__ == "__main__":
    app()
