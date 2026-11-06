"""Run-level models used by the orchestration layer."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageResult(BaseModel):
    stage: str
    status: StageStatus
    message: str = ""
    artifact_path: str = ""


class RunOptions(BaseModel):
    """Collects all CLI-level options for a full pipeline run."""

    input_files: list[Path]
    workdir: Path
    out: Path
    page_size: str = "A4"
    margins: str = "narrow"
    dpi: int = 180
    include_notes: bool = False
    resume: bool = False
    dry_run: bool = False
    config_path: Path | None = None
