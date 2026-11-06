"""Build small synthetic PPTX decks in code, so no real deck is needed.

Two decks of 17 slides each are written to a temporary directory the first time
this module is imported. Every slide has a title placeholder and a body
placeholder. Every third slide also carries a small table, and every fourth
slide has speaker notes.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

SLIDES_PER_DECK = 17


def build_deck(path: Path, label: str) -> Path:
    prs = Presentation()
    title_and_content = prs.slide_layouts[1]
    for n in range(1, SLIDES_PER_DECK + 1):
        slide = prs.slides.add_slide(title_and_content)
        slide.shapes.title.text = "Example Deck 2025" if (label == "A" and n == 1) else f"Deck {label} slide {n}"
        body = slide.placeholders[1]
        body.text_frame.text = f"First point on slide {n} of deck {label}"
        body.text_frame.add_paragraph().text = f"Second point on slide {n}"
        if n % 3 == 0:
            rows, cols = 2, 2
            table = slide.shapes.add_table(rows, cols, Inches(1), Inches(5), Inches(6), Inches(1)).table
            for r in range(rows):
                for c in range(cols):
                    table.cell(r, c).text = f"r{r}c{c}"
        if n % 4 == 0:
            slide.notes_slide.notes_text_frame.text = f"Notes for slide {n}"
    prs.save(str(path))
    return path


_DIR = Path(tempfile.mkdtemp(prefix="slidebridge-synthetic-"))
PPTX_PART1 = build_deck(_DIR / "synthetic_deck_part1.pptx", "A")
PPTX_PART2 = build_deck(_DIR / "synthetic_deck_part2.pptx", "B")
