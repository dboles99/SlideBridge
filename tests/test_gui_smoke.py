from __future__ import annotations

import tkinter as tk

import pytest


def test_gui_imports() -> None:
    """GUI module imports without side effects or import errors."""
    from slidebridge.gui import app as gui_app

    assert gui_app is not None


def test_gui_app_instantiates() -> None:
    """SlideBridgeApp can be created in environments with a display."""
    from slidebridge.gui.app import SlideBridgeApp

    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
    except Exception as exc:  # pragma: no cover - depends on runtime display
        pytest.skip(f"No display available: {exc}")

    app = SlideBridgeApp()
    try:
        app.withdraw()
        assert app.winfo_exists() == 1
        assert app.title() == "SlideBridge"
    finally:
        app.destroy()
