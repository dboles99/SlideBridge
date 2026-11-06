# SlideBridge GUI Guide

The SlideBridge GUI is a Tkinter desktop application that wraps the full CLI pipeline in a point-and-click interface. It is useful for non-technical operators, one-off jobs, and quick inspection runs.

For batch processing, scripting, or CI, use the CLI instead — see [cli.md](cli.md).

---

## Launching the GUI

```bash
# Development (recommended)
uv run slidebridge-gui

# If installed globally
slidebridge-gui
```

The window opens at 940 × 700 px (minimum 720 × 520). It is resizable.

**Requirement:** LibreOffice must be installed and `soffice` on PATH for the Render and Run Full Pipeline operations.

---

## Window layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  File   Run   Help                           [menu bar]             │
├───────────────────────────────┬─────────────────────────────────────┤
│  Input PPTX Files             │  Settings                           │
│  ┌─────────────────────────┐  │  Output DOCX: [path…]  […]          │
│  │ deck_part1.pptx         │  │  Work Dir:   [work]    […]          │
│  │ deck_part2.pptx         │  │  DPI:        [150 ▲▼]              │
│  └─────────────────────────┘  │  [Include Notes] [Resume]           │
│  [Add…] [Remove] [Clear]      │  [Dry Run]      [Verbose]           │
├───────────────────────────────┴─────────────────────────────────────┤
│  [▶ Run Full Pipeline]  [Extract]  [Render]  [Inspect]  [Clean]     │
│  [⇌ Align…]                              Stage 3/5: reconcile ████░ │
├─────────────────────────────────────────────────────────────────────┤
│  Log                                                                 │
│  [12:04:01] INFO     -- Stage: extract                              │
│  [12:04:03] INFO     Extracted 32 slides from deck_part1.pptx       │
│  [12:04:10] INFO     [DONE] extract                                 │
│  [12:04:10] INFO     -- Stage: render                               │
│  ...                                                                 │
│                        [Clear Log]  [Open Folder]  [Open Output]    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Input PPTX Files panel

Add one or more `.pptx` files to process. Files are processed in the order listed.

| Control | Keyboard | Description |
|---------|----------|-------------|
| **Add…** | `Ctrl+O` | Open a file picker — multi-select is supported |
| **Remove** | — | Remove selected items (click to select, Shift/Ctrl for multiple) |
| **Clear** | — | Remove all files from the list |

Files are stored as absolute paths. If a file is moved or deleted after adding it, the pipeline will fail with a "file not found" error.

---

## Settings panel

| Setting | Default | Description |
|---------|---------|-------------|
| **Output DOCX** | `output/review_pack.docx` | Path for the generated DOCX file. Use `[…]` to browse. |
| **Work Dir** | `work` | Directory for intermediate files (PDF, PNG, JSON). Use `[…]` to browse. |
| **DPI** | `150` | Image render resolution. Lower = smaller file; higher = sharper screenshots. Reasonable range: 96–300. |
| **Include Notes** | off | Extract speaker notes into the review pack |
| **Resume** | off | Skip re-rendering slides whose PNG files already exist and pass validation |
| **Dry Run** | off | Show pipeline stages in the log without actually running them |
| **Verbose** | off | Switch the log panel to DEBUG level (very detailed) |

---

## Action buttons

### Run Full Pipeline (`F5`)

Runs all five stages in sequence: extract → render → reconcile → build-docx → audit.

- Requires at least one PPTX file added.
- Requires LibreOffice for the render stage.
- Progress bar advances through each stage.
- On success, prompts to open the output file.
- The Run button is disabled while a pipeline is running.

### Extract

Runs only the extract stage (no LibreOffice needed). Output goes to `{work dir}/json/`.

### Render

Runs only the render stage. Requires LibreOffice. Output goes to `{work dir}/pdf/` and `{work dir}/images/`.

### Inspect

Prints a slide count summary to the log panel without processing anything.

### Clean

Prompts for confirmation, then removes the intermediate files inside the work directory (`pdf/`, `images/`, `json/`, `reconciled/`). Does not remove the output DOCX or audit files.

### Align… (`Ctrl+Shift+A`)

Opens the **Align Edited Text** dialog.

---

## Align Edited Text dialog

Use this when an editor has worked in a separate DOCX (not the review pack) and you want to merge their edits into the review pack's Edited Text column.

```
┌─────────────────────────────────────────────────────┐
│  Align Edited Text                                  │
│                                                     │
│  Review Pack DOCX:  [output/review_pack.docx]  […]  │
│  Edited DOCX:       [path/to/edited.docx]      […]  │
│  Output DOCX:       [output/aligned.docx]      […]  │
│                                                     │
│  [Run Align]  [Cancel]                              │
└─────────────────────────────────────────────────────┘
```

| Field | Description |
|-------|-------------|
| **Review Pack DOCX** | The SlideBridge-generated review pack. Pre-filled from the Output DOCX setting. |
| **Edited DOCX** | The editor's separate DOCX (e.g., the original Word file returned by the editor). |
| **Output DOCX** | Where to write the aligned result (`output/aligned.docx` by default). |

After clicking **Run Align**, the status line updates with progress. On completion, you are offered to open the output file.

---

## Log panel

The log panel shows real-time pipeline output in a dark-themed, color-coded console.

| Color | Meaning |
|-------|---------|
| Cyan | `INFO` — general progress messages |
| Yellow | `WARNING` — non-fatal issues (low confidence, etc.) |
| Red | `ERROR` — failures |
| Teal bold | Stage start markers (`-- Stage: ...`) |
| Green bold | Stage completion (`[DONE]`, `[SKIPPED]`) |

Use **Clear Log** to reset the panel before a new run. The panel does not auto-clear between runs.

**Open Output** — opens the output DOCX in the default application (Word, LibreOffice Writer, etc.).
**Open Folder** — opens the output folder in Windows Explorer.

---

## Menu reference

### File menu

| Item | Keyboard | Description |
|------|----------|-------------|
| Add PPTX Files… | `Ctrl+O` | Open file picker |
| Remove Selected | — | Remove selected items from list |
| Clear All Files | — | Clear file list |
| Open Output File | — | Open current output DOCX |
| Open Output Folder | — | Open output folder in Explorer |
| Exit | `Alt+F4` | Close the application |

### Run menu

| Item | Keyboard | Description |
|------|----------|-------------|
| Run Full Pipeline | `F5` | Full 5-stage pipeline |
| Extract Only | — | Extract stage only |
| Render Only | — | Render stage only |
| Inspect Decks | — | Print slide summary |
| Validate Manifest | — | Validate `work/reconciled/manifest.json` |
| Clean Work Folder | — | Remove intermediate files |
| Align Edited Text… | `Ctrl+Shift+A` | Open align dialog |

### Help menu

| Item | Description |
|------|-------------|
| About SlideBridge | Version info and keyboard shortcuts |

---

## Keyboard shortcuts summary

| Key | Action |
|-----|--------|
| `Ctrl+O` | Add PPTX files |
| `F5` | Run full pipeline |
| `Ctrl+Shift+A` | Open Align dialog |
| `Alt+F4` | Exit |

---

## Progress bar

The progress bar in the action bar tracks stages of a full pipeline run:

```
Stage 3/5: reconcile  [████████░░]
```

Stages: `extract` → `render` → `reconcile` → `build-docx` → `audit`

The bar fills as each stage completes. On failure, the label reads "Failed" and the bar stops at the last completed stage.

---

## Typical workflow

**New job (first run):**

1. Launch: `uv run slidebridge-gui`
2. Click **Add…** and select all PPTX files for the job
3. Set **Output DOCX** to the desired delivery path
4. Set **DPI** (default 150 is fine for most jobs; use 180 for higher quality)
5. Optionally enable **Include Notes**
6. Press `F5` or click **Run Full Pipeline**
7. Watch the log panel; progress bar advances through stages
8. On success, click **Open Output** or **Yes** in the completion dialog

**Rebuild DOCX only (images already rendered):**

1. Add the same PPTX files
2. Enable **Resume** — the render stage will be skipped
3. Press `F5`

**Align an editor's DOCX into the review pack:**

1. Press `Ctrl+Shift+A` or go to **Run → Align Edited Text…**
2. Set **Review Pack DOCX** to the review pack
3. Set **Edited DOCX** to the editor's file
4. Set **Output DOCX** to the desired output path
5. Click **Run Align**

---

## Troubleshooting

**"Add at least one PPTX file before running"**
The Input PPTX Files list is empty. Use **Add…** first.

**"These files no longer exist"**
A file was moved or renamed after it was added. Remove and re-add it.

**Render stage shows ERROR in log**
LibreOffice is not installed or not on PATH. Verify with `soffice --version` in a terminal.

**"No manifest.json found" when validating**
Run the full pipeline first. The manifest is created during the reconcile stage.

**Output DOCX is very large**
Reduce DPI (try 120 or 96). The default 150 DPI targets readability on A4; higher values increase file size significantly for 60+ slide decks.

**GUI appears frozen during render**
The render stage runs LibreOffice as a subprocess and can take 30–90 seconds for a large deck. The log panel will update when each stage completes. Do not close the window.

**Log shows garbled characters on Windows**
This should not occur — the GUI log handler is configured with `legacy_windows=False` to avoid cp1252 encoding errors. If seen, check the Windows console code page with `chcp`.
