"""SlideBridge data models."""

from slidebridge.models.audit import AuditRow
from slidebridge.models.manifest import InputDeck, RunManifest, RunSummary
from slidebridge.models.run import RunOptions, StageResult, StageStatus
from slidebridge.models.shape import BoundingBox, TextBlock, TextRun
from slidebridge.models.slide import SlideRecord

__all__ = [
    "AuditRow",
    "BoundingBox",
    "InputDeck",
    "RunManifest",
    "RunOptions",
    "RunSummary",
    "SlideRecord",
    "StageResult",
    "StageStatus",
    "TextBlock",
    "TextRun",
]
