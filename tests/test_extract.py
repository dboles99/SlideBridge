"""Unit tests for the extraction layer."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from slidebridge.extract.shape_classifier import classify_shape
from slidebridge.extract.title_detector import detect_title
from slidebridge.extract.notes_extractor import extract_notes
from slidebridge.models.shape import BoundingBox, TextBlock
from tests.synthetic_decks import PPTX_PART1


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_block(
    order: int,
    text: str,
    role: str = "body",
    top: int = 0,
    left: int = 0,
    width: int = 100,
    height: int = 50,
) -> TextBlock:
    return TextBlock(
        block_id=f"slide-b{order:03d}",
        order=order,
        shape_id=order,
        shape_type="TEXT_BOX",
        role=role,
        bbox=BoundingBox(left=left, top=top, width=width, height=height),
        text=text,
        paragraphs=[text],
    )


# ── shape_classifier ─────────────────────────────────────────────────────────

def _mock_shape(
    shape_type_val=None,
    is_placeholder=False,
    ph_type=None,
    has_text_frame=False,
    has_table=False,
):
    from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

    shape = MagicMock()
    shape.shape_type = shape_type_val or MSO_SHAPE_TYPE.TEXT_BOX
    shape.is_placeholder = is_placeholder
    shape.has_text_frame = has_text_frame
    shape.has_table = has_table

    if is_placeholder and ph_type is not None:
        shape.placeholder_format = MagicMock()
        shape.placeholder_format.type = ph_type

    return shape


def test_classify_table_shape():
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shape = _mock_shape(shape_type_val=MSO_SHAPE_TYPE.TABLE, has_table=True)
    assert classify_shape(shape) == "table"


def test_classify_group_shape():
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shape = _mock_shape(shape_type_val=MSO_SHAPE_TYPE.GROUP)
    assert classify_shape(shape) == "group"


def test_classify_title_placeholder():
    from pptx.enum.shapes import PP_PLACEHOLDER
    shape = _mock_shape(is_placeholder=True, ph_type=PP_PLACEHOLDER.TITLE, has_text_frame=True)
    assert classify_shape(shape) == "title"


def test_classify_body_placeholder():
    from pptx.enum.shapes import PP_PLACEHOLDER
    shape = _mock_shape(is_placeholder=True, ph_type=PP_PLACEHOLDER.BODY, has_text_frame=True)
    assert classify_shape(shape) == "body"


def test_classify_footer_placeholder():
    from pptx.enum.shapes import PP_PLACEHOLDER
    shape = _mock_shape(is_placeholder=True, ph_type=PP_PLACEHOLDER.FOOTER)
    assert classify_shape(shape) == "footer"


def test_classify_textbox():
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shape = _mock_shape(shape_type_val=MSO_SHAPE_TYPE.TEXT_BOX, has_text_frame=True)
    assert classify_shape(shape) == "body"


# ── title_detector ────────────────────────────────────────────────────────────

def _mock_slide_with_title(title_text: str):
    from pptx.enum.shapes import PP_PLACEHOLDER

    tf = MagicMock()
    tf.text = title_text

    ph_fmt = MagicMock()
    ph_fmt.type = PP_PLACEHOLDER.TITLE

    shape = MagicMock()
    shape.is_placeholder = True
    shape.placeholder_format = ph_fmt
    shape.has_text_frame = True
    shape.text_frame = tf

    slide = MagicMock()
    slide.shapes = [shape]
    return slide


def test_detect_title_from_placeholder():
    slide = _mock_slide_with_title("Medical Affairs Overview")
    title, source = detect_title(slide, [])
    assert title == "Medical Affairs Overview"
    assert source == "placeholder"


def test_detect_title_fallback_to_block():
    slide = MagicMock()
    slide.shapes = []
    block = _make_block(1, "Fallback Title", role="title")
    title, source = detect_title(slide, [block])
    assert title == "Fallback Title"
    assert source == "textbox"


def test_detect_title_inferred_from_first_block():
    slide = MagicMock()
    slide.shapes = []
    block = _make_block(1, "Some body text", role="body")
    title, source = detect_title(slide, [block])
    assert title == "Some body text"
    assert source == "inferred"


def test_detect_title_empty_slide():
    slide = MagicMock()
    slide.shapes = []
    title, source = detect_title(slide, [])
    assert title == ""
    assert source == "fallback"


# ── notes_extractor ───────────────────────────────────────────────────────────

def test_extract_notes_no_notes_slide():
    slide = MagicMock()
    slide.has_notes_slide = False
    assert extract_notes(slide) == ""


def test_extract_notes_with_text():
    tf = MagicMock()
    tf.text = "  Speaker note here  "

    notes_slide = MagicMock()
    notes_slide.notes_text_frame = tf

    slide = MagicMock()
    slide.has_notes_slide = True
    slide.notes_slide = notes_slide

    assert extract_notes(slide) == "Speaker note here"


def test_extract_notes_exception_returns_empty():
    from unittest.mock import PropertyMock
    slide = MagicMock()
    slide.has_notes_slide = True
    # Make accessing slide.notes_slide raise, so the try/except in extract_notes catches it
    type(slide).notes_slide = PropertyMock(side_effect=Exception("broken"))
    assert extract_notes(slide) == ""


# ── extract_deck on a synthetic deck ─────────────────────────────────────────────────



def test_extract_deck_synthetic_part1():
    from slidebridge.extract.pptx_reader import extract_deck

    slides = extract_deck(PPTX_PART1, file_index=1, include_notes=True)
    assert len(slides) == 17
    for slide in slides:
        assert slide.slide_number >= 1
        assert slide.source_file == PPTX_PART1.name
        assert slide.slide_uid.startswith(PPTX_PART1.stem)
        assert slide.title  # every slide should have some title


def test_extract_deck_slide1_title():
    from slidebridge.extract.pptx_reader import extract_deck

    slides = extract_deck(PPTX_PART1, file_index=1)
    assert slides[0].title == "Example Deck 2025"
    assert slides[0].title_source in ("placeholder", "textbox", "inferred")
