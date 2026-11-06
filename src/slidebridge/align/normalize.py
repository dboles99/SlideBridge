"""Text normalisation for SlideBridge alignment.

Both sides of the match (extracted PPT text and edited DOCX text) are
normalised before comparison so that differences in smart quotes, em-dashes,
full-width characters, and whitespace do not prevent a match.
"""

from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    """Return a lightly cleaned version of *text* suitable for display."""
    if not text:
        return ""
    # Full-width space → regular space
    text = text.replace("\u3000", " ")
    # Smart quotes → straight quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    # Common dashes → hyphen
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    # Arrow characters
    text = text.replace("\u2192", "->").replace("\u2190", "<-")
    # Middle dot / interpunct
    text = text.replace("\u30fb", " ").replace("\u00b7", " ")
    # Tilde variants
    text = text.replace("\uff5e", "-")
    # Tabs → space
    text = text.replace("\t", " ")
    # Collapse runs of whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove doubled-up quotes like ""word""
    text = re.sub(r'"{2,}', '"', text)
    return text.strip()


def fingerprint(text: str) -> str:
    """Return a lowercase, punctuation-stripped token string for fuzzy matching."""
    text = normalize_text(text).lower()
    # Keep alphanumeric, % / . - + space
    text = re.sub(r"[^a-z0-9%/.\-+ ]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
