"""Unit tests for reconcile: reading order, confidence, warnings."""

from __future__ import annotations

from slidebridge.models.shape import BoundingBox, TextBlock
from slidebridge.models.slide import SlideRecord
from slidebridge.reconcile.confidence import score_slide
from slidebridge.reconcile.reading_order import reorder_slide
from slidebridge.reconcile.warnings import flag_slide


# ── Helpers ──────────────────────────────────────────────────────────────────

def _block(
    order: int,
    text: str,
    role: str = "body",
    top: int = 0,
    left: int = 0,
    shape_type: str = "TEXT_BOX",
) -> TextBlock:
    return TextBlock(
        block_id=f"uid-b{order:03d}",
        order=order,
        shape_id=order,
        shape_type=shape_type,
        role=role,
        bbox=BoundingBox(left=left, top=top, width=500000, height=300000),
        text=text,
        paragraphs=[text],
    )


def _slide(**kwargs) -> SlideRecord:
    defaults = dict(
        source_file="test.pptx",
        source_file_index=1,
        slide_number=1,
        slide_uid="test-slide-001",
        title="Test Slide",
        title_source="placeholder",
        raw_text_char_count=100,
        shape_count=3,
        text_shape_count=3,
    )
    defaults.update(kwargs)
    return SlideRecord(**defaults)


# ── reading_order ─────────────────────────────────────────────────────────────

def test_title_block_always_first():
    blocks = [
        _block(1, "Body text", role="body", top=500000),
        _block(2, "My Title", role="title", top=100000),
    ]
    slide = _slide(text_blocks=blocks)
    result = reorder_slide(slide)
    assert result.text_blocks[0].role == "title"
    assert result.text_blocks[0].text == "My Title"


def test_footer_block_always_last():
    blocks = [
        _block(1, "Footer", role="footer", top=100000),
        _block(2, "Body", role="body", top=500000),
    ]
    slide = _slide(text_blocks=blocks)
    result = reorder_slide(slide)
    assert result.text_blocks[-1].role == "footer"


def test_body_blocks_sorted_top_then_left():
    # Tops must differ by more than ROW_TOLERANCE_EMU (457200) to be separate bands.
    # Row 1 (top=100000): "Above both columns content"
    # Row 2 (top=700000, diff=600000 > 457200): "Left …" (left=100000) then "Right …" (left=3000000)
    blocks = [
        _block(1, "Right column content here", role="body", top=700000, left=3000000),
        _block(2, "Left column content here", role="body", top=700000, left=100000),
        _block(3, "Above both columns content", role="body", top=100000, left=500000),
    ]
    slide = _slide(text_blocks=blocks)
    result = reorder_slide(slide, merge_fragments=False)
    body = [b for b in result.text_blocks if b.role == "body"]
    assert body[0].text == "Above both columns content"
    assert body[1].text == "Left column content here"
    assert body[2].text == "Right column content here"


def test_order_numbers_reassigned_sequentially():
    blocks = [_block(10, "B", top=500000), _block(20, "A", top=100000)]
    slide = _slide(text_blocks=blocks)
    result = reorder_slide(slide)
    orders = [b.order for b in result.text_blocks]
    assert orders == list(range(1, len(orders) + 1))


def test_empty_slide_returns_unchanged():
    slide = _slide(text_blocks=[])
    result = reorder_slide(slide)
    assert result.text_blocks == []


def test_ordered_char_count_updated():
    blocks = [_block(1, "Hello World", top=0)]
    slide = _slide(text_blocks=blocks)
    result = reorder_slide(slide)
    assert result.ordered_text_char_count == len("Hello World")


# ── confidence ────────────────────────────────────────────────────────────────

def test_perfect_slide_confidence_is_one():
    slide = _slide(text_blocks=[_block(1, "Good text", role="body")])
    result = score_slide(slide)
    assert result.confidence == 1.0


def test_no_title_penalty():
    slide = _slide(title_source="fallback", text_blocks=[_block(1, "text")])
    result = score_slide(slide)
    assert result.confidence < 1.0


def test_zero_text_nonblank_image_penalty():
    slide = _slide(raw_text_char_count=0, shape_count=5, text_blocks=[])
    result = score_slide(slide)
    assert result.confidence < 1.0


def test_grouped_shapes_penalty():
    blocks = [_block(1, "x", shape_type="GROUP")]
    slide = _slide(text_blocks=blocks)
    result = score_slide(slide)
    assert result.confidence < 1.0


def test_confidence_clamped_to_zero():
    # Apply every penalty at once — order must start at 1
    blocks = [_block(i, "x", shape_type="GROUP") for i in range(1, 11)]
    slide = _slide(
        title_source="fallback",
        raw_text_char_count=0,
        shape_count=10,
        text_blocks=blocks,
    )
    result = score_slide(slide)
    assert result.confidence >= 0.0


# ── warnings ──────────────────────────────────────────────────────────────────

def test_no_detected_title_flag():
    slide = _slide(title_source="fallback")
    result = flag_slide(slide)
    assert "no_detected_title" in result.warnings


def test_image_without_text_flag():
    slide = _slide(raw_text_char_count=0, shape_count=3, text_blocks=[])
    result = flag_slide(slide)
    assert "image_without_text" in result.warnings


def test_table_detected_flag():
    slide = _slide(table_count=1)
    result = flag_slide(slide)
    assert "table_detected" in result.warnings


def test_confidence_below_threshold_flag():
    slide = _slide(confidence=0.4)
    result = flag_slide(slide, warn_low_confidence=True)
    assert "confidence_below_threshold" in result.warnings


def test_no_flags_on_clean_slide():
    slide = _slide(
        title_source="placeholder",
        raw_text_char_count=500,
        shape_count=3,
        confidence=0.95,
        text_blocks=[_block(1, "content")],
    )
    result = flag_slide(slide, warn_low_confidence=True)
    assert result.warnings == []
