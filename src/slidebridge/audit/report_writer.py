"""Write run_report.json."""

from __future__ import annotations

import logging
from pathlib import Path

import orjson

from slidebridge.constants import RUN_REPORT_FILENAME
from slidebridge.models.manifest import RunManifest

logger = logging.getLogger(__name__)


def write_run_report(manifest: RunManifest, out_dir: Path) -> Path:
    """Serialise the manifest summary to run_report.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if manifest.summary is None:
        manifest.compute_summary()
    out_path = out_dir / RUN_REPORT_FILENAME
    out_path.write_bytes(
        orjson.dumps(manifest.model_dump(include={"run_id", "tool_version", "summary", "inputs"}),
                     option=orjson.OPT_INDENT_2)
    )
    logger.info("Wrote run report -> %s", out_path)
    return out_path
