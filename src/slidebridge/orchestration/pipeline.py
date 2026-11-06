"""Full pipeline orchestration for `slidebridge run`."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from rich.console import Console

from slidebridge.models.run import RunOptions, StageResult, StageStatus

logger = logging.getLogger(__name__)
# Use ANSI output (legacy_windows=False) so Rich markup and stage separators
# render correctly on Windows without hitting cp1252 encoding errors.
console = Console(file=sys.stdout, legacy_windows=False)


def run_pipeline(opts: RunOptions) -> bool:
    """Execute all pipeline stages in order. Returns True on success."""
    results: list[StageResult] = []

    stages = [
        ("extract", _stage_extract),
        ("render", _stage_render),
        ("reconcile", _stage_reconcile),
        ("build-docx", _stage_build_docx),
        ("audit", _stage_audit),
    ]

    context: dict[str, object] = {"opts": opts}

    for name, fn in stages:
        logger.info("-- Stage: %s --", name)
        if opts.dry_run:
            result = StageResult(stage=name, status=StageStatus.SKIPPED, message="dry-run")
        else:
            try:
                result = fn(opts, context)
            except Exception as exc:
                logger.exception("Stage %s failed: %s", name, exc)
                result = StageResult(stage=name, status=StageStatus.FAILED, message=str(exc))

        results.append(result)
        _log_stage(result)

        if result.status == StageStatus.FAILED:
            console.print(f"[bold red]Pipeline aborted at stage: {name}[/bold red]")
            return False

    _print_summary(results, opts.out)
    return True


def _stage_extract(opts: RunOptions, ctx: dict[str, object]) -> StageResult:
    from slidebridge.orchestration.jobs import cmd_extract

    json_dir = opts.workdir / "json"

    if opts.resume:
        # Only extract decks whose JSON output is missing
        pending = [p for p in opts.input_files if not (json_dir / f"{p.stem}.json").exists()]
        already = len(opts.input_files) - len(pending)
        if already:
            logger.info("--resume: skipping %d already-extracted deck(s)", already)
        input_files = pending
    else:
        input_files = opts.input_files

    if input_files:
        cmd_extract(
            input_files,
            out=json_dir,
            include_notes=opts.include_notes,
            detect_titles=True,
            pretty=False,
        )
    # Collect all JSON paths (including previously extracted ones)
    all_json_paths = [json_dir / f"{p.stem}.json" for p in opts.input_files]
    ctx["json_paths"] = [p for p in all_json_paths if p.exists()]
    return StageResult(stage="extract", status=StageStatus.DONE,
                       artifact_path=str(json_dir))


def _stage_render(opts: RunOptions, ctx: dict[str, object]) -> StageResult:
    from pptx import Presentation

    from slidebridge.orchestration.jobs import cmd_render
    from slidebridge.render.render_manifest import validate_render_output

    pdf_dir = opts.workdir / "pdf"
    img_dir = opts.workdir / "images"

    if opts.resume:
        pending = []
        for pptx_path in opts.input_files:
            try:
                slide_count = len(Presentation(str(pptx_path)).slides)
            except Exception:
                slide_count = 0
            errors = validate_render_output(img_dir, pptx_path.stem, slide_count)
            if errors:
                pending.append(pptx_path)
            else:
                logger.info("--resume: skipping already-rendered %s", pptx_path.name)
        input_files = pending
    else:
        input_files = opts.input_files

    if input_files:
        cmd_render(input_files, pdf_dir=pdf_dir, img_dir=img_dir,
                   dpi=opts.dpi, fmt="png")
    ctx["img_dir"] = img_dir
    return StageResult(stage="render", status=StageStatus.DONE,
                       artifact_path=str(img_dir))


def _stage_reconcile(opts: RunOptions, ctx: dict[str, object]) -> StageResult:
    from slidebridge.orchestration.jobs import cmd_reconcile

    json_paths: list[Path] = ctx["json_paths"]  # type: ignore[assignment]
    img_dir: Path = ctx.get("img_dir", opts.workdir / "images")  # type: ignore[assignment]
    reconciled_dir = opts.workdir / "reconciled"
    manifest_path = cmd_reconcile(
        json_paths,
        out=reconciled_dir,
        merge_fragments=True,
        warn_low_confidence=True,
        img_dir=img_dir,
    )
    ctx["manifest_path"] = manifest_path
    return StageResult(stage="reconcile", status=StageStatus.DONE,
                       artifact_path=str(manifest_path))


def _stage_build_docx(opts: RunOptions, ctx: dict[str, object]) -> StageResult:
    from slidebridge.orchestration.jobs import cmd_build_docx

    manifest_path: Path = ctx["manifest_path"]  # type: ignore[assignment]
    img_dir: Path = ctx["img_dir"]  # type: ignore[assignment]
    cmd_build_docx(
        manifest=manifest_path,
        images=img_dir,
        out=opts.out,
        page_size=opts.page_size,
        margins=opts.margins,
    )
    return StageResult(stage="build-docx", status=StageStatus.DONE,
                       artifact_path=str(opts.out))


def _stage_audit(opts: RunOptions, ctx: dict[str, object]) -> StageResult:
    from slidebridge.orchestration.jobs import cmd_audit

    manifest_path: Path = ctx["manifest_path"]  # type: ignore[assignment]
    audit_dir = opts.out.parent
    cmd_audit(manifest=manifest_path, out=audit_dir)
    return StageResult(stage="audit", status=StageStatus.DONE,
                       artifact_path=str(audit_dir))


def _log_stage(result: StageResult) -> None:
    colour = {"done": "green", "failed": "red", "skipped": "yellow"}.get(
        result.status.value, "white"
    )
    msg = f"[{colour}][{result.status.value.upper()}][/{colour}] {result.stage}"
    if result.artifact_path:
        msg += f" -> {result.artifact_path}"
    if result.message:
        msg += f" ({result.message})"
    console.print(msg)


def _print_summary(results: list[StageResult], out: Path) -> None:
    console.rule("[bold green]Pipeline complete[/bold green]")
    for r in results:
        _log_stage(r)
    console.print(f"\n[bold]Output:[/bold] {out}")
