"""Convert a PPTX file to PDF using LibreOffice headless.

LibreOffice must be installed and 'soffice' must be on PATH (or SOFFICE_PATH
env var pointing to the executable).
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

_SOFFICE_CANDIDATES = [
    "soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/lib/libreoffice/program/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_soffice() -> str:
    """Return the path to soffice, checking env override first."""
    env_path = os.environ.get("SOFFICE_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    import shutil
    for candidate in _SOFFICE_CANDIDATES:
        found = shutil.which(candidate) or (Path(candidate).exists() and candidate)
        if found:
            return str(found)
    raise RuntimeError(
        "LibreOffice not found. Install LibreOffice and ensure 'soffice' is on PATH, "
        "or set the SOFFICE_PATH environment variable."
    )


@retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
def convert_to_pdf(pptx_path: Path, out_dir: Path) -> Path:
    """Convert a PPTX file to PDF. Returns the path of the generated PDF.

    Raises RuntimeError if conversion fails or output is missing.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    soffice = find_soffice()

    cmd = [
        soffice,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(out_dir),
        str(pptx_path),
    ]
    logger.debug("LibreOffice cmd: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed for {pptx_path.name}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    pdf_path = out_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError(
            f"LibreOffice reported success but PDF not found at {pdf_path}. "
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    logger.info("PDF created: %s", pdf_path)
    return pdf_path
