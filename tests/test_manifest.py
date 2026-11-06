"""Unit tests for manifest model correctness."""

from __future__ import annotations

from slidebridge.models.manifest import InputDeck, RunManifest, RunSummary
from slidebridge.models.slide import SlideRecord


def _slide(num: int, source: str = "test.pptx", confidence: float = 1.0) -> SlideRecord:
    return SlideRecord(
        source_file=source,
        source_file_index=1,
        slide_number=num,
        slide_uid=f"test-slide-{num:03d}",
        title=f"Slide {num}",
        title_source="placeholder",
        confidence=confidence,
        image_path=f"work/images/test/slide_{num:03d}.png",
    )


def test_compute_summary_counts():
    slides = [_slide(i) for i in range(1, 18)]  # 17 slides
    deck = InputDeck(source_file="test.pptx", slide_count=17)
    m = RunManifest(slides=slides, inputs=[deck])
    s = m.compute_summary()
    assert s.total_files == 1
    assert s.total_slides == 17
    assert s.total_images == 17  # all have image_path set


def test_compute_summary_low_confidence():
    slides = [_slide(i, confidence=0.3) for i in range(1, 6)]
    m = RunManifest(slides=slides, inputs=[InputDeck(source_file="x.pptx", slide_count=5)])
    s = m.compute_summary()
    assert s.low_confidence_slides == 5


def test_compute_summary_empty_inputs():
    m = RunManifest(slides=[], inputs=[])
    s = m.compute_summary()
    assert s.total_files == 0
    assert s.total_slides == 0


def test_manifest_serialise_roundtrip():
    import orjson
    slides = [_slide(1), _slide(2)]
    deck = InputDeck(source_file="part1.pptx", slide_count=2)
    m = RunManifest(slides=slides, inputs=[deck])
    m.compute_summary()
    raw = orjson.dumps(m.model_dump())
    restored = RunManifest.model_validate(orjson.loads(raw))
    assert len(restored.slides) == 2
    assert restored.inputs[0].source_file == "part1.pptx"
