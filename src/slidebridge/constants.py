"""Project-wide constants for SlideBridge."""

from pathlib import Path

# ── Version ───────────────────────────────────────────────────────────────────
TOOL_VERSION = "0.1.0"

# ── Page layout ───────────────────────────────────────────────────────────────
# A4 in EMUs (English Metric Units used by python-docx)
A4_WIDTH_EMU = 11906400   # 210 mm
A4_HEIGHT_EMU = 16838400  # 297 mm

# Narrow margins in EMUs (12.7 mm = 0.5 inch)
NARROW_MARGIN_EMU = 457200

# Image insertion width in inches (fits within A4 narrow margins)
IMAGE_WIDTH_INCHES = 6.7

# ── Rendering ─────────────────────────────────────────────────────────────────
DEFAULT_DPI = 180
DEFAULT_IMAGE_FORMAT = "png"
MAX_IMAGE_WIDTH_PX = 2000

# ── Confidence scoring ────────────────────────────────────────────────────────
CONFIDENCE_PENALTY_NO_TITLE = 0.10
CONFIDENCE_PENALTY_HIGH_IMAGE_TEXT_MISMATCH = 0.20
CONFIDENCE_PENALTY_MANY_FRAGMENTS = 0.10
CONFIDENCE_PENALTY_GROUPED_SHAPES = 0.15
CONFIDENCE_PENALTY_CHART_HEAVY = 0.20
CONFIDENCE_PENALTY_ZERO_TEXT_NONBLANK_IMAGE = 0.35
CONFIDENCE_LOW_THRESHOLD = 0.60

# ── Reading order ─────────────────────────────────────────────────────────────
# Shapes within this many EMUs vertically are considered the same row
ROW_TOLERANCE_EMU = 457200  # ~12.7 mm / 0.5 inch

# ── File naming ───────────────────────────────────────────────────────────────
SLIDE_IMAGE_STEM = "slide_{:03d}"   # slide_001.png, slide_002.png ...

# ── Work directories ──────────────────────────────────────────────────────────
DEFAULT_WORKDIR = Path("work")
DEFAULT_PDF_SUBDIR = "pdf"
DEFAULT_IMAGES_SUBDIR = "images"
DEFAULT_JSON_SUBDIR = "json"
DEFAULT_RECONCILED_SUBDIR = "reconciled"
DEFAULT_LOGS_SUBDIR = "logs"

# ── Output ────────────────────────────────────────────────────────────────────
DEFAULT_DOCX_NAME = "review_pack.docx"
DEFAULT_AUDIT_SUBDIR = "output"
MANIFEST_FILENAME = "manifest.json"
SLIDES_CSV_FILENAME = "slides.csv"
WARNINGS_CSV_FILENAME = "warnings.csv"
RUN_REPORT_FILENAME = "run_report.json"

# ── DOCX table column widths (inches) ─────────────────────────────────────────
# 4-column layout: Order | Original Extracted Text | Edited Text | Notes
COL_ORDER_WIDTH = 0.4
COL_ORIGINAL_WIDTH = 2.8
COL_EDITED_WIDTH = 2.8
COL_NOTES_WIDTH = 0.7
