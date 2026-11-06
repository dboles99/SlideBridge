"""Manifest model — top-level object representing one pipeline run."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from slidebridge.constants import TOOL_VERSION
from slidebridge.models.slide import SlideRecord


class InputDeck(BaseModel):
    """Metadata about one source PPTX file."""

    source_file: str
    source_hash_sha256: str = ""
    slide_count: int = Field(ge=1)
    pdf_file: str = ""
    image_dir: str = ""


class RunSummary(BaseModel):
    total_files: int = Field(ge=0)
    total_slides: int = Field(ge=0)
    total_images: int = Field(ge=0)
    low_confidence_slides: int = Field(ge=0)
    warnings: int = Field(ge=0)


class RunManifest(BaseModel):
    """Full manifest produced at the end of a reconcile run."""

    run_id: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    )
    tool_version: str = TOOL_VERSION
    inputs: list[InputDeck] = Field(default_factory=list)
    slides: list[SlideRecord] = Field(default_factory=list)
    summary: RunSummary | None = None

    def compute_summary(self) -> RunSummary:
        low_conf = sum(1 for s in self.slides if s.confidence < 0.60)
        total_warnings = sum(len(s.warnings) for s in self.slides)
        images_present = sum(1 for s in self.slides if s.image_path)
        self.summary = RunSummary(
            total_files=len(self.inputs),
            total_slides=len(self.slides),
            total_images=images_present,
            low_confidence_slides=low_conf,
            warnings=total_warnings,
        )
        return self.summary
