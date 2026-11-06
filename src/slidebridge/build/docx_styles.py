"""Apply A4 page layout and narrow margins to a python-docx Document."""

from __future__ import annotations

from docx import Document
from docx.shared import Emu

from slidebridge.constants import A4_HEIGHT_EMU, A4_WIDTH_EMU, NARROW_MARGIN_EMU


def apply_page_layout(
    doc: Document,
    page_size: str = "A4",
    margins: str = "narrow",
) -> None:
    """Set page dimensions and margins on all sections of the document."""
    margin_emu = _resolve_margins(margins)

    for section in doc.sections:
        if page_size.upper() == "A4":
            section.page_width = Emu(A4_WIDTH_EMU)
            section.page_height = Emu(A4_HEIGHT_EMU)
        section.top_margin = Emu(margin_emu)
        section.bottom_margin = Emu(margin_emu)
        section.left_margin = Emu(margin_emu)
        section.right_margin = Emu(margin_emu)


def _resolve_margins(preset: str) -> int:
    presets = {
        "narrow": NARROW_MARGIN_EMU,          # 12.7 mm / 0.5 inch
        "normal": 1143000,                    # 25.4 mm / 1 inch
        "moderate": 914400,                   # 19.05 mm / 0.75 inch
    }
    return presets.get(preset.lower(), NARROW_MARGIN_EMU)
