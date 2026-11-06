"""SlideBridge GUI — Tkinter front-end for the SlideBridge pipeline."""

from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# ── Stages (matches pipeline order) ──────────────────────────────────────────
_STAGES = ["extract", "render", "reconcile", "build-docx", "audit"]

# ── Log formatter used in the GUI log panel ───────────────────────────────────
_LOG_FMT = logging.Formatter("[%(asctime)s] %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")


# ── Queue-based log handler (thread-safe) ────────────────────────────────────
class _QueueHandler(logging.Handler):
    """Forwards log records into a queue for the main GUI thread to consume."""

    def __init__(self, q: queue.Queue[logging.LogRecord]) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        _queue.put_nowait(record)


# Module-level queue so it can be shared without passing self everywhere
_queue: queue.Queue[logging.LogRecord] = queue.Queue()


# ── Main application window ───────────────────────────────────────────────────
class SlideBridgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SlideBridge")
        self.geometry("940x700")
        self.minsize(720, 520)

        self._input_files: list[Path] = []
        self._running = False
        self._stage_step = 0

        self._build_menu()
        self._build_ui()
        self._install_log_handler()
        self._poll_log_queue()

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        self.config(menu=menu)

        # File
        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add PPTX Files…",   accelerator="Ctrl+O", command=self._add_files)
        file_menu.add_command(label="Remove Selected",                          command=self._remove_selected)
        file_menu.add_command(label="Clear All Files",                          command=self._clear_files)
        file_menu.add_separator()
        file_menu.add_command(label="Open Output File",                         command=self._open_output_file)
        file_menu.add_command(label="Open Output Folder",                       command=self._open_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",               accelerator="Alt+F4", command=self.destroy)

        # Run
        run_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Full Pipeline",  accelerator="F5",      command=self._run_pipeline)
        run_menu.add_separator()
        run_menu.add_command(label="Extract Only",                               command=self._run_extract)
        run_menu.add_command(label="Render Only",                                command=self._run_render)
        run_menu.add_separator()
        run_menu.add_command(label="Inspect Decks",                              command=self._run_inspect)
        run_menu.add_command(label="Validate Manifest",                          command=self._run_validate)
        run_menu.add_separator()
        run_menu.add_command(label="Clean Work Folder",                          command=self._run_clean)
        run_menu.add_separator()
        run_menu.add_command(label="Align Edited Text…", accelerator="Ctrl+Shift+A",
                             command=self._open_align_dialog)

        # Help
        help_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About SlideBridge", command=self._show_about)

        self.bind_all("<Control-o>",       lambda _e: self._add_files())
        self.bind_all("<F5>",              lambda _e: self._run_pipeline())
        self.bind_all("<Control-A>",       lambda _e: self._open_align_dialog())  # Ctrl+Shift+A

    # ── UI layout ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=6)
        top.pack(fill="both", expand=False)
        top.columnconfigure(0, weight=3)
        top.columnconfigure(1, weight=2)

        self._build_files_panel(top)
        self._build_settings_panel(top)
        self._build_actions_bar()
        self._build_log_panel()

    def _build_files_panel(self, parent: ttk.Frame) -> None:
        lf = ttk.LabelFrame(parent, text="Input PPTX Files", padding=4)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)

        self._file_list = tk.Listbox(lf, selectmode=tk.EXTENDED, height=7, activestyle="dotbox")
        self._file_list.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(lf, orient="vertical", command=self._file_list.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._file_list.config(yscrollcommand=sb.set)

        btn_row = ttk.Frame(lf)
        btn_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Button(btn_row, text="Add…",   command=self._add_files).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Remove", command=self._remove_selected).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Clear",  command=self._clear_files).pack(side="left", padx=2)

    def _build_settings_panel(self, parent: ttk.Frame) -> None:
        lf = ttk.LabelFrame(parent, text="Settings", padding=4)
        lf.grid(row=0, column=1, sticky="nsew")
        lf.columnconfigure(1, weight=1)

        # Output DOCX path
        ttk.Label(lf, text="Output DOCX:").grid(row=0, column=0, sticky="w", pady=2)
        self._output_var = tk.StringVar(value="output/review_pack.docx")
        out_row = ttk.Frame(lf)
        out_row.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Entry(out_row, textvariable=self._output_var).pack(side="left", fill="x", expand=True)
        ttk.Button(out_row, text="…", width=3, command=self._browse_output).pack(side="left")

        # Work directory
        ttk.Label(lf, text="Work Dir:").grid(row=1, column=0, sticky="w", pady=2)
        self._workdir_var = tk.StringVar(value="work")
        wd_row = ttk.Frame(lf)
        wd_row.grid(row=1, column=1, sticky="ew", padx=(4, 0))
        ttk.Entry(wd_row, textvariable=self._workdir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(wd_row, text="…", width=3, command=self._browse_workdir).pack(side="left")

        # DPI spinbox
        ttk.Label(lf, text="DPI:").grid(row=2, column=0, sticky="w", pady=2)
        self._dpi_var = tk.StringVar(value="150")
        dpi_frame = ttk.Frame(lf)
        dpi_frame.grid(row=2, column=1, sticky="w", padx=(4, 0))
        ttk.Spinbox(dpi_frame, from_=72, to=600, increment=30,
                    textvariable=self._dpi_var, width=6).pack(side="left")

        # Option checkboxes
        self._notes_var   = tk.BooleanVar(value=False)
        self._resume_var  = tk.BooleanVar(value=False)
        self._dryrun_var  = tk.BooleanVar(value=False)
        self._verbose_var = tk.BooleanVar(value=False)

        chk = ttk.Frame(lf)
        chk.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Checkbutton(chk, text="Include Notes", variable=self._notes_var).pack(side="left")
        ttk.Checkbutton(chk, text="Resume",        variable=self._resume_var).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(chk, text="Dry Run",       variable=self._dryrun_var).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(chk, text="Verbose",       variable=self._verbose_var,
                        command=self._apply_verbose).pack(side="left", padx=(8, 0))

    def _build_actions_bar(self) -> None:
        bar = ttk.Frame(self, padding=(6, 2))
        bar.pack(fill="x")

        self._run_btn = ttk.Button(bar, text="▶  Run Full Pipeline", command=self._run_pipeline)
        self._run_btn.pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Extract", command=self._run_extract).pack(side="left", padx=2)
        ttk.Button(bar, text="Render",  command=self._run_render).pack(side="left", padx=2)
        ttk.Button(bar, text="Inspect", command=self._run_inspect).pack(side="left", padx=2)
        ttk.Button(bar, text="Clean",   command=self._run_clean).pack(side="left", padx=2)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, text="⇌ Align…", command=self._open_align_dialog).pack(side="left", padx=2)

        self._stage_label = ttk.Label(bar, text="")
        self._stage_label.pack(side="right", padx=(0, 6))
        self._progress = ttk.Progressbar(bar, length=200, mode="determinate",
                                         maximum=len(_STAGES))
        self._progress.pack(side="right")

    def _build_log_panel(self) -> None:
        lf = ttk.LabelFrame(self, text="Log", padding=4)
        lf.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)

        self._log_text = scrolledtext.ScrolledText(
            lf, height=16, wrap="word", state="disabled",
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
        )
        self._log_text.grid(row=0, column=0, sticky="nsew")

        self._log_text.tag_config("INFO",    foreground="#9cdcfe")
        self._log_text.tag_config("WARNING", foreground="#dcdcaa")
        self._log_text.tag_config("ERROR",   foreground="#f44747")
        self._log_text.tag_config("STAGE",   foreground="#4ec9b0", font=("Consolas", 9, "bold"))
        self._log_text.tag_config("DONE",    foreground="#608b4e", font=("Consolas", 9, "bold"))

        btn_row = ttk.Frame(lf)
        btn_row.grid(row=1, column=0, sticky="e", pady=(4, 0))
        ttk.Button(btn_row, text="Open Output", command=self._open_output_file).pack(side="right", padx=2)
        ttk.Button(btn_row, text="Open Folder", command=self._open_output_folder).pack(side="right", padx=2)
        ttk.Button(btn_row, text="Clear Log",   command=self._clear_log).pack(side="right", padx=2)

    # ── Logging ───────────────────────────────────────────────────────────────

    def _install_log_handler(self) -> None:
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(_QueueHandler(_queue))

    def _apply_verbose(self) -> None:
        level = logging.DEBUG if self._verbose_var.get() else logging.INFO
        logging.getLogger().setLevel(level)

    def _poll_log_queue(self) -> None:
        try:
            while True:
                record = _queue.get_nowait()
                self._append_log(record)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_log_queue)

    def _append_log(self, record: logging.LogRecord) -> None:
        msg = _LOG_FMT.format(record)

        # Detect stage starts for progress bar
        if "-- Stage:" in msg:
            for i, stage in enumerate(_STAGES):
                if stage in msg:
                    self._stage_step = i + 1
                    self.after(0, self._update_progress)
                    break
            tag = "STAGE"
        elif "[DONE]" in msg or "[SKIPPED]" in msg:
            tag = "DONE"
        elif record.levelno >= logging.ERROR:
            tag = "ERROR"
        elif record.levelno >= logging.WARNING:
            tag = "WARNING"
        else:
            tag = "INFO"

        self._log_text.config(state="normal")
        self._log_text.insert("end", msg + "\n", tag)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _clear_log(self) -> None:
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _update_progress(self) -> None:
        self._progress["value"] = self._stage_step
        name = _STAGES[self._stage_step - 1] if 0 < self._stage_step <= len(_STAGES) else ""
        self._stage_label.config(text=f"Stage {self._stage_step}/{len(_STAGES)}: {name}")

    # ── File management ───────────────────────────────────────────────────────

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PPTX Files",
            filetypes=[("PowerPoint Files", "*.pptx"), ("All Files", "*.*")],
        )
        for p in paths:
            path = Path(p)
            if path not in self._input_files:
                self._input_files.append(path)
                self._file_list.insert("end", str(path))

    def _remove_selected(self) -> None:
        selection: tuple[int, ...] = self._file_list.curselection()  # type: ignore[no-untyped-call]
        for i in reversed(selection):
            self._file_list.delete(i)
            self._input_files.pop(i)

    def _clear_files(self) -> None:
        self._file_list.delete(0, "end")
        self._input_files.clear()

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Choose output DOCX path",
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
        )
        if path:
            self._output_var.set(path)

    def _browse_workdir(self) -> None:
        path = filedialog.askdirectory(title="Select Work Directory")
        if path:
            self._workdir_var.set(path)

    # ── Open output helpers ───────────────────────────────────────────────────

    def _open_output_file(self) -> None:
        p = Path(self._output_var.get())
        if p.exists():
            os.startfile(str(p))
        else:
            messagebox.showwarning("Not Found", f"Output file not found:\n{p}")

    def _open_output_folder(self) -> None:
        p = Path(self._output_var.get()).parent
        if p.exists():
            os.startfile(str(p))
        else:
            messagebox.showwarning("Not Found", f"Output folder not found:\n{p}")

    # ── UI lock/unlock ────────────────────────────────────────────────────────

    def _validate_inputs(self) -> bool:
        if not self._input_files:
            messagebox.showwarning("No Input", "Add at least one PPTX file before running.")
            return False
        missing = [str(p) for p in self._input_files if not p.exists()]
        if missing:
            messagebox.showerror("File Not Found",
                                 "These files no longer exist:\n" + "\n".join(missing))
            return False
        return True

    def _lock_ui(self) -> None:
        self._running = True
        self._run_btn.config(state="disabled")
        self._progress["value"] = 0
        self._stage_step = 0
        self._stage_label.config(text="Starting…")

    def _unlock_ui(self, success: bool) -> None:
        self._running = False
        self._run_btn.config(state="normal")
        if success:
            self._progress["value"] = len(_STAGES)
            self._stage_label.config(text="Done")
        else:
            self._stage_label.config(text="Failed")

    # ── Pipeline execution ────────────────────────────────────────────────────

    def _run_pipeline(self) -> None:
        if self._running or not self._validate_inputs():
            return
        self._lock_ui()
        self._clear_log()

        from slidebridge.models.run import RunOptions
        from slidebridge.orchestration.pipeline import run_pipeline

        opts = RunOptions(
            input_files=list(self._input_files),
            workdir=Path(self._workdir_var.get()),
            out=Path(self._output_var.get()),
            dpi=int(self._dpi_var.get()),
            include_notes=self._notes_var.get(),
            resume=self._resume_var.get(),
            dry_run=self._dryrun_var.get(),
        )

        def run() -> None:
            success = False
            try:
                success = run_pipeline(opts)
            except Exception as exc:
                logging.exception("Pipeline error: %s", exc)
            self.after(0, self._unlock_ui, success)
            if success:
                self.after(0, self._on_pipeline_success)

        threading.Thread(target=run, daemon=True).start()

    def _on_pipeline_success(self) -> None:
        out = Path(self._output_var.get())
        if messagebox.askyesno("Done", f"Pipeline complete!\n\n{out}\n\nOpen the file now?"):
            self._open_output_file()

    def _run_extract(self) -> None:
        if self._running or not self._validate_inputs():
            return
        self._lock_ui()
        self._clear_log()

        from slidebridge.orchestration.jobs import cmd_extract

        out = Path(self._workdir_var.get()) / "json"
        files = list(self._input_files)
        notes = self._notes_var.get()

        def run() -> None:
            try:
                cmd_extract(files, out=out, include_notes=notes, detect_titles=True, pretty=True)
            except Exception as exc:
                logging.exception("Extract error: %s", exc)
            self.after(0, self._unlock_ui, True)

        threading.Thread(target=run, daemon=True).start()

    def _run_render(self) -> None:
        if self._running or not self._validate_inputs():
            return
        self._lock_ui()
        self._clear_log()

        from slidebridge.orchestration.jobs import cmd_render

        wd = Path(self._workdir_var.get())
        files = list(self._input_files)
        dpi = int(self._dpi_var.get())

        def run() -> None:
            try:
                cmd_render(files, pdf_dir=wd / "pdf", img_dir=wd / "images",
                           dpi=dpi, fmt="png")
            except Exception as exc:
                logging.exception("Render error: %s", exc)
            self.after(0, self._unlock_ui, True)

        threading.Thread(target=run, daemon=True).start()

    def _run_inspect(self) -> None:
        if not self._validate_inputs():
            return
        from slidebridge.orchestration.jobs import cmd_inspect
        cmd_inspect(list(self._input_files))

    def _run_validate(self) -> None:
        manifest = Path(self._workdir_var.get()) / "reconciled" / "manifest.json"
        if not manifest.exists():
            messagebox.showwarning(
                "Not Found",
                f"No manifest.json found at:\n{manifest}\n\nRun the pipeline first.",
            )
            return
        from slidebridge.orchestration.jobs import cmd_validate
        ok = cmd_validate(manifest)
        if ok:
            messagebox.showinfo("Valid", "Manifest is valid.")
        else:
            messagebox.showerror("Invalid", "Manifest validation failed. See log for details.")

    def _run_clean(self) -> None:
        wd = Path(self._workdir_var.get())
        if not messagebox.askyesno("Clean", f"Remove intermediate files in:\n{wd}\n\nContinue?"):
            return
        from slidebridge.orchestration.jobs import cmd_clean
        cmd_clean(wd)
        messagebox.showinfo("Done", f"Cleaned {wd}")

    # ── Align dialog ──────────────────────────────────────────────────────────

    def _open_align_dialog(self) -> None:
        """Open the Align Edited Text dialog."""
        dlg = _AlignDialog(self)
        dlg.grab_set()

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About SlideBridge",
            "SlideBridge  v0.1.0\n\n"
            "Converts PPTX slide decks into A4 review-pack DOCX files\n"
            "with per-slide screenshots and editable text tables.\n\n"
            "LibreOffice must be installed for the Render stage.\n\n"
            "Commands:\n"
            "  Ctrl+O          Add PPTX files\n"
            "  F5              Run full pipeline\n"
            "  Ctrl+Shift+A    Align edited text",
        )


# ── Align dialog ─────────────────────────────────────────────────────────────

class _AlignDialog(tk.Toplevel):
    """Modal dialog for the Align Edited Text command."""

    def __init__(self, parent: SlideBridgeApp) -> None:
        super().__init__(parent)
        self._parent = parent
        self.title("Align Edited Text")
        self.resizable(False, False)
        self._running = False

        pad_x = 6
        pad_y = 3

        # ── Review Pack row ──
        ttk.Label(self, text="Review Pack DOCX:").grid(
            row=0,
            column=0,
            sticky="w",
            padx=pad_x,
            pady=pad_y,
        )
        self._review_var = tk.StringVar()
        # Pre-fill from parent output path if it exists
        parent_out = parent._output_var.get()
        if parent_out:
            self._review_var.set(parent_out)
        row0 = ttk.Frame(self)
        row0.grid(row=0, column=1, sticky="ew", padx=pad_x, pady=pad_y)
        ttk.Entry(row0, textvariable=self._review_var, width=46).pack(side="left", fill="x", expand=True)
        ttk.Button(row0, text="…", width=3,
                   command=lambda: self._browse(self._review_var, "open")).pack(side="left")

        # ── Edited Doc row ──
        ttk.Label(self, text="Edited DOCX:").grid(
            row=1,
            column=0,
            sticky="w",
            padx=pad_x,
            pady=pad_y,
        )
        self._edited_var = tk.StringVar()
        row1 = ttk.Frame(self)
        row1.grid(row=1, column=1, sticky="ew", padx=pad_x, pady=pad_y)
        ttk.Entry(row1, textvariable=self._edited_var, width=46).pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text="…", width=3,
                   command=lambda: self._browse(self._edited_var, "open")).pack(side="left")

        # ── Output row ──
        ttk.Label(self, text="Output DOCX:").grid(
            row=2,
            column=0,
            sticky="w",
            padx=pad_x,
            pady=pad_y,
        )
        self._out_var = tk.StringVar(value="output/aligned.docx")
        row2 = ttk.Frame(self)
        row2.grid(row=2, column=1, sticky="ew", padx=pad_x, pady=pad_y)
        ttk.Entry(row2, textvariable=self._out_var, width=46).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="…", width=3,
                   command=lambda: self._browse(self._out_var, "save")).pack(side="left")

        # ── Status label ──
        self._status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._status_var, foreground="#888888").grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            padx=pad_x,
            pady=pad_y,
        )

        # ── Buttons ──
        btn_row = ttk.Frame(self)
        btn_row.grid(row=4, column=0, columnspan=2, pady=(4, 8))
        self._run_btn = ttk.Button(btn_row, text="Run Align", command=self._run)
        self._run_btn.pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        self.columnconfigure(1, weight=1)
        self.update_idletasks()
        # Centre over parent
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _browse(self, var: tk.StringVar, mode: str) -> None:
        if mode == "open":
            p = filedialog.askopenfilename(
                title="Select DOCX",
                filetypes=[("Word Document", "*.docx"), ("All Files", "*.*")],
            )
        else:
            p = filedialog.asksaveasfilename(
                title="Save aligned DOCX as",
                defaultextension=".docx",
                filetypes=[("Word Document", "*.docx")],
            )
        if p:
            var.set(p)

    def _run(self) -> None:
        review = Path(self._review_var.get())
        edited = Path(self._edited_var.get())
        out    = Path(self._out_var.get())

        if not review.exists():
            messagebox.showerror("Not Found", f"Review pack not found:\n{review}", parent=self)
            return
        if not edited.exists():
            messagebox.showerror("Not Found", f"Edited DOCX not found:\n{edited}", parent=self)
            return

        self._run_btn.config(state="disabled")
        self._status_var.set("Running…")

        from slidebridge.orchestration.jobs import cmd_align

        def run() -> None:
            try:
                cmd_align(review_pack=review, edited_doc=edited, out=out)
                self.after(0, self._on_done, True, out)
            except Exception as exc:
                logging.exception("Align error: %s", exc)
                self.after(0, self._on_done, False, out)

        threading.Thread(target=run, daemon=True).start()

    def _on_done(self, success: bool, out: Path) -> None:
        self._run_btn.config(state="normal")
        if success:
            self._status_var.set(f"Done — {out.name}")
            if messagebox.askyesno("Done", f"Alignment complete!\n\n{out}\n\nOpen now?", parent=self):
                os.startfile(str(out))
        else:
            self._status_var.set("Failed — see log for details")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = SlideBridgeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
