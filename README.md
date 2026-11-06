# SlideBridge

**[Read the wiki](https://github.com/dboles99/SlideBridge/wiki)** for how it works, the evidence, the design decisions and the limits.

A command-line tool that turns PowerPoint decks into a Word review pack: one table per slide with a screenshot, the extracted text, and an empty column for an editor's changes.

**简体中文：** SlideBridge 把一个或多个 PowerPoint（`.pptx`）文件转换成便于审校的 Word（`.docx`）文件：每张幻灯片对应一个表格，包含幻灯片截图、提取出的文字，以及留给编辑填写修改内容的空列。截图需要安装 LibreOffice。

**繁體中文：** SlideBridge 將一個或多個 PowerPoint（`.pptx`）檔案轉換成便於審校的 Word（`.docx`）檔案：每張投影片對應一個表格，包含投影片截圖、擷取出的文字，以及留給編輯填寫修改內容的空欄。截圖需要安裝 LibreOffice。

## What it does

The `run` command chains five stages, and each stage is also a command of its own:

1. `extract`: read each slide with python-pptx and write JSON (title, text blocks with positions, tables, optional speaker notes).
2. `render`: convert the deck to PDF with LibreOffice, then to one PNG per slide with PyMuPDF.
3. `reconcile`: put text blocks in reading order, merge small fragments, and score each slide's confidence.
4. `build-docx`: write the A4 review pack.
5. `audit`: write `slides.csv`, `warnings.csv` and `run_report.json`.

`align` takes a finished review pack plus a separately edited DOCX and fills the review pack's edited-text column by matching text. `validate` checks a manifest against its JSON schema, `clean` removes the work folder, and `slidebridge-gui` opens a Tkinter front end for the same pipeline.

## Quick start

Needs Python 3.11 or later. LibreOffice (`soffice` on the PATH) is needed for the `render` stage and therefore for `run`; `extract`, `reconcile` and the tests other than the render test do not need it.

```bash
git clone https://github.com/dboles99/SlideBridge.git
cd SlideBridge
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

`uv sync --group dev` also works, and `uv.lock` is included.

## Example

Make a small synthetic deck (17 slides, with a table on every third slide and notes on every fourth), then run the pipeline on it:

```bash
.venv/bin/python -m examples.make_sample_deck
.venv/bin/slidebridge run input/sample.pptx --workdir work --out output/review_pack.docx --dpi 100
```

On one run on Windows with LibreOffice, this produced `output/review_pack.docx` plus the audit files in about 7 seconds. `output/run_report.json` summarised it as:

```json
{"total_files": 1, "total_slides": 17, "total_images": 17, "low_confidence_slides": 0, "warnings": 5}
```

The five warnings are `table_detected` on slides 3, 6, 9, 12 and 15. `output/slides.csv` has one row per slide with its title, confidence and warning count. See [docs/cli.md](docs/cli.md) for every command and option, and [docs/gui.md](docs/gui.md) for the GUI.

## Design notes

- Each stage reads and writes plain files under the work folder (`work/json`, `work/pdf`, `work/images`, `work/reconciled/manifest.json`), so a stage can be re-run alone and `--resume` skips renders that already validate.
- Render output is validated: page count must match slide count, and zero-byte images fail the stage.
- Slides with low confidence (no title, many tiny fragments, grouped shapes, chart-heavy slides) are flagged in the audit files so an editor knows where to look first.
- Heavy imports are deferred inside commands, so `--help` is quick.

## Limits

- The reading order and confidence scores are heuristics. They have been exercised only on synthetic decks in this public repository, so expect odd results on complex layouts, charts and grouped shapes.
- Rendering depends on LibreOffice, so screenshots can differ from what PowerPoint shows.
- `align` matches text approximately; check its output by eye.
- `source_hash_sha256` and `pdf_file` are empty in `run_report.json` in the run above.
- The test suite has one test that needs LibreOffice. Without `soffice` on the PATH it is skipped (44 passed, 1 skipped on my run); with it, all 45 pass. The GUI smoke test skips itself if no display is available.
- Tested on Windows with Python 3.12 only.

## Licence

Apache-2.0. See [LICENSE](LICENSE).

Designed and authored by Daniel Boles; implemented with coding agents.
