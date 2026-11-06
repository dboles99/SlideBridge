"""Segment edited DOCX text into matchable units.

Segments are sentence/bullet-sized chunks.  We err on the side of keeping
them slightly larger (2–3 sentences) rather than over-fragmenting, because
the PPT extraction often merges bullets into single blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from slidebridge.align.normalize import fingerprint, normalize_text


@dataclass
class EditedSegment:
    index: int
    text: str        # display text (normalised)
    fp: str          # fingerprint for matching


def split_into_sentences(text: str) -> list[str]:
    """Split *text* into sentence-ish chunks without over-fragmenting."""
    text = normalize_text(text)
    # Split on: sentence-end + whitespace, newlines, bullet-like prefixes
    raw = re.split(r"(?<=[.!?])\s+|\n+|(?=•)|(?=·)|(?=\d+\.\s)", text)
    parts = [p.strip() for p in raw if p and p.strip()]
    return parts


def build_segments(full_text: str) -> list[EditedSegment]:
    """Return a flat list of EditedSegment objects from *full_text*."""
    parts = split_into_sentences(full_text)
    return [
        EditedSegment(index=i, text=part, fp=fingerprint(part))
        for i, part in enumerate(parts)
        if part
    ]
