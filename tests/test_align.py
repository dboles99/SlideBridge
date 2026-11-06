from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def sample_review_pack(tmp_path: Path) -> Path:
    """Minimal review-pack DOCX with one heading and one 4-col table."""
    from docx import Document

    doc = Document()
    doc.add_heading("Slide 1 - Test Slide", level=1)

    table = doc.add_table(rows=2, cols=4)
    headers = ["Order", "Original Extracted Text", "Edited Text", "Notes"]
    for idx, header in enumerate(headers):
        table.rows[0].cells[idx].text = header

    table.rows[1].cells[0].text = "1"
    table.rows[1].cells[1].text = "Original text here"

    out = tmp_path / "review_pack.docx"
    doc.save(str(out))
    return out


@pytest.fixture()
def sample_edited_doc(tmp_path: Path) -> Path:
    """Edited DOCX containing text that should align exactly."""
    from docx import Document

    doc = Document()
    doc.add_paragraph("Original text here")

    out = tmp_path / "edited.docx"
    doc.save(str(out))
    return out


def test_align_produces_output(
    sample_review_pack: Path,
    sample_edited_doc: Path,
    tmp_path: Path,
) -> None:
    """Align command writes an output docx and populates edited/notes cells."""
    from docx import Document

    from slidebridge.orchestration.jobs import cmd_align

    out = tmp_path / "aligned.docx"
    cmd_align(review_pack=sample_review_pack, edited_doc=sample_edited_doc, out=out)

    assert out.exists()
    assert out.stat().st_size > 0

    doc = Document(str(out))
    assert len(doc.tables) == 1

    row = doc.tables[0].rows[1].cells
    assert row[2].text.strip() != ""
    assert "Unchanged" in row[3].text or "Exact match" in row[3].text
