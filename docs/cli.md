# SlideBridge CLI Reference

SlideBridge is invoked via `uv run slidebridge` (development) or `slidebridge` (installed).

The GUI is a separate entry point — see [gui.md](gui.md).

---

## Quick start

```bash
# Install dependencies
uv sync --group dev

# Verify CLI is available
uv run slidebridge --help

# Verify LibreOffice (required for render stage)
soffice --version

# Run the full pipeline on one or more decks
uv run slidebridge run "input/deck.pptx" \
  --workdir work \
  --out output/review_pack.docx \
  --dpi 180
```

---

## Global options

Common options:

| Option | Scope | Default | Description |
|--------|-------|---------|-------------|
| `--config` / `-c` | all commands | auto-detect `slidebridge.yaml` | Path to config file |
| `--verbose` / `-v` | all commands | `false` | Enable DEBUG-level logging |
| `--dry-run` | `run` only | `false` | Show pipeline stages without executing them |

---

## Commands

### `init`

Create project scaffolding and a sample `slidebridge.yaml`.

```bash
uv run slidebridge init
```

Creates:
- `slidebridge.yaml` — sample config
- `input/`, `work/`, `output/` directories
- `logs/` directory

---

### `inspect`

Read PPTX files and print a slide count summary. Does not extract or render anything.

```bash
uv run slidebridge inspect input/*.pptx
```

**Arguments:**
- One or more `.pptx` file paths

**Output:** Console table showing file name, slide count, and whether titles were detected.

---

### `extract`

Parse PPTX files and write structured JSON for each slide.

```bash
uv run slidebridge extract input/*.pptx \
  --out work/json \
  --include-notes \
  --detect-titles \
  --pretty
```

**Arguments:**
- One or more `.pptx` file paths

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--out` | `work/json` | Output directory for JSON files |
| `--include-notes` | `false` | Extract speaker notes |
| `--detect-titles` | `true` | Auto-detect slide titles via placeholder then fallback |
| `--pretty` | `false` | Pretty-print JSON (readable, larger files) |

**Output:** One `{deck_stem}.json` per input file in `--out` directory.

Each JSON file contains a list of `SlideRecord` objects with:
- `slide_number`, `slide_uid`, `title`, `title_source`
- `text_blocks` with `bbox`, `text`, `shape_type`, `role`
- `warnings`, `confidence`, `notes_present`

---

### `render`

Convert PPTX files to PDF via LibreOffice, then render each page to PNG.

```bash
uv run slidebridge render input/*.pptx \
  --pdf-dir work/pdf \
  --img-dir work/images \
  --dpi 180 \
  --format png
```

**Arguments:**
- One or more `.pptx` file paths

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--pdf-dir` | `work/pdf` | Directory for intermediate PDF files |
| `--img-dir` | `work/images` | Root directory for PNG output |
| `--dpi` | `180` | Render resolution (72–600) |
| `--format` | `png` | Image format (`png`) |

**Output:**
```
work/pdf/{deck_stem}.pdf
work/images/{deck_stem}/slide_001.png
work/images/{deck_stem}/slide_002.png
...
```

**Requirement:** LibreOffice must be installed and `soffice` must be on PATH.

**Fail conditions:**
- `soffice` not found on PATH
- PDF page count does not match PPTX slide count
- PNG count does not match PDF page count
- Any zero-byte image file

---

### `reconcile`

Apply reading-order heuristics and confidence scoring to extracted JSON files.

```bash
uv run slidebridge reconcile work/json/*.json \
  --out work/reconciled \
  --merge-fragments \
  --warn-low-confidence \
  --img-dir work/images
```

**Arguments:**
- One or more extracted `.json` files

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--out` | `work/reconciled` | Output directory for reconciled manifest |
| `--merge-fragments` | `true` | Merge small adjacent text fragments |
| `--warn-low-confidence` | `true` | Flag slides with confidence below threshold |
| `--img-dir` | `None` | Images root dir — links `image_path` into each slide record |

**Output:** `work/reconciled/manifest.json` — a `RunManifest` with all slides in order.

**Reading-order logic:**
1. Title placeholder is always first
2. Shapes sorted by vertical band (top position ± row tolerance)
3. Within band, sorted left-to-right
4. Tables preserved as atomic units
5. Footer-like items placed last

**Confidence scoring:** Base 1.0, subtract penalties for no title, high image/text mismatch, many tiny fragments, grouped shapes, chart-heavy slide, zero text with nonblank image.

---

### `build-docx`

Build the A4 DOCX review pack from a reconciled manifest.

```bash
uv run slidebridge build-docx \
  --manifest work/reconciled/manifest.json \
  --images work/images \
  --out output/review_pack.docx \
  --page-size A4 \
  --margins narrow
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--manifest` | (required) | Path to `manifest.json` |
| `--images` | (required) | Root directory containing slide PNGs |
| `--out` | `output/review_pack.docx` | Output `.docx` path |
| `--page-size` | `A4` | Page size |
| `--margins` | `narrow` | Margin preset |

**Per-slide output structure:**

```
Heading 1:  Slide 12 - Medical Affairs Activities
Metadata:   Source: Part 1 | Slide: 12 | Confidence: 0.87 | Warnings: 1
Image:      [rendered PNG, centered, max 6.7 inches wide]
Warning:    [Extraction warning block if confidence is low]
Table:      Order | Original Extracted Text | Edited Text | Notes
            1     | Medical Affairs Activ…   |             |
            2     | Second text block…       |             |
```

---

### `audit`

Write audit output files from a reconciled manifest.

```bash
uv run slidebridge audit \
  --manifest work/reconciled/manifest.json \
  --out output
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--manifest` | (required) | Path to `manifest.json` |
| `--out` | `output` | Directory for audit files |

**Output files:**

| File | Description |
|------|-------------|
| `slides.csv` | One row per slide: slide_uid, title, confidence, warning_count, char_count, image_exists |
| `warnings.csv` | One row per warning: slide_uid, warning flag name |
| `run_report.json` | Summary: total_files, total_slides, total_images, low_confidence_slides, warnings |

---

### `run`

One-shot full pipeline: extract → render → reconcile → build-docx → audit.

```bash
uv run slidebridge run \
  "input/deck_part1.pptx" \
  "input/deck_part2.pptx" \
  --workdir work \
  --out output/review_pack.docx \
  --page-size A4 \
  --margins narrow \
  --dpi 180 \
  --include-notes
```

**Arguments:**
- One or more `.pptx` file paths

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--workdir` | `work` | Working directory for intermediate files |
| `--out` | `output/review_pack.docx` | Output `.docx` path |
| `--page-size` | `A4` | Page size |
| `--margins` | `narrow` | Margin preset |
| `--dpi` | `180` | Render DPI (72–600) |
- `--include-notes` | `false` | Extract speaker notes |
| `--resume` | `false` | Skip already-rendered artifacts |
| `--dry-run` | `false` | Show stages without executing |

**Exit codes:** `0` on success, `1` on any failure.

**Working directory structure created:**
```
work/
  pdf/{deck_stem}.pdf
  images/{deck_stem}/slide_001.png ...
  json/{deck_stem}.json
  reconciled/manifest.json
  logs/run.log
  logs/errors.log

output/
  review_pack.docx
  slides.csv
  warnings.csv
  run_report.json
```

---

### `validate`

Validate a `manifest.json` against the JSON schema.

```bash
uv run slidebridge validate work/reconciled/manifest.json
```

**Arguments:**
- Path to a `manifest.json`

**Exit codes:** `0` if valid, `1` if schema validation fails.

---

### `clean`

Remove intermediate work artifacts (`pdf/`, `images/`, `json/`, `reconciled/`).

```bash
uv run slidebridge clean --workdir work
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--workdir` | `work` | Working directory to clean |

Does not remove `output/` or `logs/`.

---

### `align`

Populate the **Edited Text** column in a review-pack DOCX by matching it against a separately edited DOCX.

This is useful when an editor has worked in a plain DOCX without the review-pack structure — the `align` command maps their edits back into the correct table cells.

```bash
uv run slidebridge align \
  output/review_pack.docx \
  "input/edited_deck.docx" \
  --out output/aligned.docx
```

**Arguments:**
- `review_pack` — the SlideBridge review-pack DOCX
- `edited_doc` — the edited DOCX to align against

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--out` | `output/aligned.docx` | Output aligned DOCX path |

---

## Config file

`slidebridge.yaml` is auto-detected in the current directory. Override with `--config path/to/file.yaml`.

```yaml
project:
  name: slidebridge
  log_level: INFO        # DEBUG | INFO | WARNING | ERROR

input:
  glob:
    - "input/*.pptx"

render:
  engine: libreoffice
  dpi: 180
  image_format: png
  optimize_images: true
  max_width_px: 2000

extract:
  include_notes: true
  detect_titles: true
  merge_text_fragments: true

reconcile:
  sort_primary: top
  sort_secondary: left
  row_tolerance_emu: 457200   # ~1 cm in EMU
  warn_low_confidence: true

docx:
  page_size: A4
  margins: narrow
  insert_source_filename: true
  image_width_inches: 6.7
  table_layout: fixed
  include_warning_block: true

audit:
  write_csv: true
  write_json: true
```

---

## Common workflows

### First run on a new set of decks

```bash
uv run slidebridge init
# place PPTX files in input/
uv run slidebridge run input/*.pptx --workdir work --out output/review_pack.docx --dpi 180
```

### Rebuild DOCX without re-rendering

```bash
uv run slidebridge build-docx \
  --manifest work/reconciled/manifest.json \
  --images work/images \
  --out output/review_pack.docx
```

### Debug a specific stage

```bash
# Extract only (no LibreOffice needed)
uv run slidebridge extract input/*.pptx --out work/json --pretty --verbose

# Inspect slide count before committing to a full run
uv run slidebridge inspect input/*.pptx
```

### Resume after render interruption

```bash
uv run slidebridge run input/*.pptx --workdir work --out output/review_pack.docx --resume
```

### Validate after changing models

```bash
uv run slidebridge validate work/reconciled/manifest.json
```

### Align an independently-edited DOCX

```bash
uv run slidebridge align \
  output/review_pack.docx \
  "input/edited_deck.docx" \
  --out output/aligned.docx
```

---

## Development commands

```bash
# Run all tests
.venv/Scripts/python.exe -m pytest tests/ -v --tb=short   # Windows
python -m pytest tests/ -v --tb=short                      # Unix

# Lint
.venv/Scripts/ruff.exe check src/
.venv/Scripts/ruff.exe check src/ --fix

# Type check
.venv/Scripts/mypy.exe src/

# Coverage
.venv/Scripts/python.exe -m pytest tests/ --cov=src/slidebridge --cov-report=term-missing
```

---

## Quality gates

A run fails loudly (`RuntimeError`, exit code 1) on any of:

- Input PPTX cannot be opened
- LibreOffice conversion returns nonzero exit
- PDF page count ≠ PPTX slide count
- PNG count ≠ PDF page count
- Any zero-byte PNG
- Manifest fails schema validation
- Required images missing before `build-docx`

Warnings (logged, not fatal):
- Slide has low confidence score
- Possible missing chart labels
- Grouped shapes present
- No title detected
