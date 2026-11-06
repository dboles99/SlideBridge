"""Validate manifest.json against the embedded Pydantic model schema."""

from __future__ import annotations

import logging
from pathlib import Path

import orjson
from pydantic import ValidationError

from slidebridge.models.manifest import RunManifest

logger = logging.getLogger(__name__)


def validate_manifest(manifest_path: Path) -> tuple[bool, list[str]]:
    """Validate a manifest.json file. Returns (is_valid, error_messages)."""
    try:
        raw = orjson.loads(manifest_path.read_bytes())
    except Exception as exc:
        return False, [f"Cannot read/parse file: {exc}"]

    try:
        RunManifest.model_validate(raw)
        return True, []
    except ValidationError as exc:
        errors = [f"{e['loc']}: {e['msg']}" for e in exc.errors()]
        return False, errors
