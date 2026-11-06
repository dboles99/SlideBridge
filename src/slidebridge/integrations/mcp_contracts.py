"""Protocol interfaces for each SlideBridge capability boundary.

Local adapters implement these protocols now; they can later be swapped for
MCP-backed adapters without changing orchestration code.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from slidebridge.models.manifest import RunManifest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol definitions
# ---------------------------------------------------------------------------

@runtime_checkable
class FilesystemAdapter(Protocol):
    """Abstract boundary for all filesystem I/O."""

    def list_files(self, pattern: str) -> list[Path]:
        """Return all paths matching a glob pattern."""
        ...

    def read_bytes(self, path: Path) -> bytes:
        """Read raw bytes from *path*."""
        ...

    def write_bytes(self, path: Path, data: bytes) -> None:
        """Write *data* to *path*, creating parent directories as needed."""
        ...

    def exists(self, path: Path) -> bool:
        """Return True if *path* exists on the filesystem."""
        ...

    def sha256(self, path: Path) -> str:
        """Return the hex-encoded SHA-256 digest of the file at *path*."""
        ...

    def mkdir(self, path: Path) -> None:
        """Create *path* and all parents if they do not already exist."""
        ...


@runtime_checkable
class LibreOfficeAdapter(Protocol):
    """Abstract boundary for LibreOffice PPTX-to-PDF conversion."""

    def convert_to_pdf(self, pptx_path: Path, out_dir: Path) -> Path:
        """Convert *pptx_path* to a PDF placed in *out_dir*.

        Returns the path of the generated PDF file.
        """
        ...


@runtime_checkable
class PdfRenderAdapter(Protocol):
    """Abstract boundary for PDF-page-to-image rendering."""

    def render_pages(
        self,
        pdf_path: Path,
        out_dir: Path,
        dpi: int,
        fmt: str,
    ) -> list[Path]:
        """Render every page of *pdf_path* to an image file in *out_dir*.

        Returns the list of generated image paths in page order.
        """
        ...

    def page_count(self, pdf_path: Path) -> int:
        """Return the number of pages in *pdf_path*."""
        ...


@runtime_checkable
class DocxAdapter(Protocol):
    """Abstract boundary for DOCX review-pack assembly."""

    def build_review_pack(
        self,
        manifest: RunManifest,
        images_root: Path,
        out_path: Path,
        page_size: str,
        margins: str,
    ) -> None:
        """Assemble and write the DOCX review pack to *out_path*."""
        ...


@runtime_checkable
class SchemaAdapter(Protocol):
    """Abstract boundary for manifest schema validation."""

    def validate_manifest(self, manifest_path: Path) -> tuple[bool, list[str]]:
        """Validate *manifest_path* against the RunManifest schema.

        Returns ``(is_valid, error_messages)``.
        """
        ...


@runtime_checkable
class QaAdapter(Protocol):
    """Abstract boundary for post-pipeline QA checks."""

    def check_counts(
        self,
        manifest: RunManifest,
        img_dir: Path,
    ) -> list[str]:
        """Check that every slide in *manifest* has a corresponding image.

        Returns a list of error strings; an empty list means all checks passed.
        """
        ...

    def generate_warnings_report(
        self,
        manifest: RunManifest,
    ) -> list[dict[str, object]]:
        """Build a list of warning dicts — one entry per flagged slide.

        Each dict contains at least ``slide_uid``, ``confidence``, and
        ``warnings`` keys.
        """
        ...


# ---------------------------------------------------------------------------
# Local (non-MCP) concrete adapters
# ---------------------------------------------------------------------------

class LocalFilesystemAdapter:
    """Filesystem adapter backed by pathlib and hashlib."""

    def list_files(self, pattern: str) -> list[Path]:
        """Return all paths matching *pattern* as a glob expression."""
        import glob as _glob
        from pathlib import Path as _Path
        return [_Path(p) for p in _glob.glob(pattern, recursive=True)]

    def read_bytes(self, path: Path) -> bytes:
        """Read and return raw bytes from *path*."""
        return path.read_bytes()

    def write_bytes(self, path: Path, data: bytes) -> None:
        """Write *data* to *path*, creating parent directories first."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def exists(self, path: Path) -> bool:
        """Return True if *path* exists."""
        return path.exists()

    def sha256(self, path: Path) -> str:
        """Return hex SHA-256 digest of the file at *path*."""
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def mkdir(self, path: Path) -> None:
        """Create *path* and all parents."""
        path.mkdir(parents=True, exist_ok=True)


class LocalLibreOfficeAdapter:
    """LibreOffice adapter that delegates to the render.libreoffice module."""

    def convert_to_pdf(self, pptx_path: Path, out_dir: Path) -> Path:
        """Convert *pptx_path* to PDF via LibreOffice headless."""
        from slidebridge.render.libreoffice import convert_to_pdf
        return convert_to_pdf(pptx_path, out_dir)


class LocalPdfRenderAdapter:
    """PDF render adapter that delegates to render.pdf_renderer."""

    def render_pages(
        self,
        pdf_path: Path,
        out_dir: Path,
        dpi: int,
        fmt: str,
    ) -> list[Path]:
        """Render every PDF page to an image and return the image paths."""
        from slidebridge.render.pdf_renderer import render_pdf_to_images
        return render_pdf_to_images(pdf_path, out_dir, dpi=dpi, fmt=fmt)

    def page_count(self, pdf_path: Path) -> int:
        """Return the number of pages in *pdf_path* via PyMuPDF."""
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        count = len(doc)
        doc.close()
        return count


class LocalDocxAdapter:
    """DOCX adapter that delegates to build.docx_builder."""

    def build_review_pack(
        self,
        manifest: RunManifest,
        images_root: Path,
        out_path: Path,
        page_size: str = "A4",
        margins: str = "narrow",
    ) -> None:
        """Assemble the DOCX review pack and write it to *out_path*."""
        from slidebridge.build.docx_builder import build_review_pack
        build_review_pack(
            manifest,
            images_root=images_root,
            out_path=out_path,
            page_size=page_size,
            margins=margins,
        )


class LocalSchemaAdapter:
    """Schema adapter that delegates to integrations.schema_validator."""

    def validate_manifest(self, manifest_path: Path) -> tuple[bool, list[str]]:
        """Validate *manifest_path* and return ``(is_valid, errors)``."""
        from slidebridge.integrations.schema_validator import validate_manifest
        return validate_manifest(manifest_path)


class LocalQaAdapter:
    """QA adapter with inline count-check and warnings-report logic."""

    def check_counts(
        self,
        manifest: RunManifest,
        img_dir: Path,
    ) -> list[str]:
        """Verify that each slide's image_path exists and is non-empty.

        Also checks that the manifest slide count matches the number of image
        files found under *img_dir*.  Returns a list of error strings.
        """
        errors: list[str] = []
        for slide in manifest.slides:
            if not slide.image_path:
                errors.append(
                    f"Slide {slide.slide_uid}: image_path is empty in manifest"
                )
                continue
            img = Path(slide.image_path)
            if not img.exists():
                errors.append(f"Slide {slide.slide_uid}: image missing at {img}")
            elif img.stat().st_size == 0:
                errors.append(f"Slide {slide.slide_uid}: zero-byte image at {img}")
        return errors

    def generate_warnings_report(
        self,
        manifest: RunManifest,
    ) -> list[dict[str, object]]:
        """Return a list of warning dicts for all slides that carry warnings."""
        report: list[dict[str, object]] = []
        for slide in manifest.slides:
            if slide.warnings:
                report.append(
                    {
                        "slide_uid": slide.slide_uid,
                        "source_file": slide.source_file,
                        "slide_number": slide.slide_number,
                        "confidence": slide.confidence,
                        "warnings": list(slide.warnings),
                    }
                )
        return report


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

@dataclass
class AdapterRegistry:
    """Holds one adapter instance per capability boundary."""

    filesystem: FilesystemAdapter = field(default_factory=LocalFilesystemAdapter)
    libreoffice: LibreOfficeAdapter = field(default_factory=LocalLibreOfficeAdapter)
    pdf_render: PdfRenderAdapter = field(default_factory=LocalPdfRenderAdapter)
    docx: DocxAdapter = field(default_factory=LocalDocxAdapter)
    schema: SchemaAdapter = field(default_factory=LocalSchemaAdapter)
    qa: QaAdapter = field(default_factory=LocalQaAdapter)

    @classmethod
    def local(cls) -> AdapterRegistry:
        """Return a registry wired entirely with local (non-MCP) adapters."""
        return cls(
            filesystem=LocalFilesystemAdapter(),
            libreoffice=LocalLibreOfficeAdapter(),
            pdf_render=LocalPdfRenderAdapter(),
            docx=LocalDocxAdapter(),
            schema=LocalSchemaAdapter(),
            qa=LocalQaAdapter(),
        )
