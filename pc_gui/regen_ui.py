"""Regenerate the *_ui.py files from the ui/*.ui layouts via pyside6-uic.

- Standalone:  python regen_ui.py         (force regenerate all)
- From main.py: ensure_ui() regenerates only when a .ui is newer than its .py,
  so you can just edit the .ui in pyside6-designer and re-run the app.
"""

from __future__ import annotations

import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# (source .ui, generated .py) pairs to keep in sync.
UI_FILES = [
    (os.path.join(HERE, "ui", "main_window.ui"),     os.path.join(HERE, "ui_main_window.py")),
    (os.path.join(HERE, "ui", "settings_dialog.ui"),  os.path.join(HERE, "ui_settings_dialog.py")),
    (os.path.join(HERE, "ui", "waveform_dialog.ui"),  os.path.join(HERE, "ui_waveform_dialog.py")),
]


def regen(force: bool = False) -> bool:
    """Run pyside6-uic for each stale .ui. Returns True if anything (re)generated."""
    regenerated = False
    for ui_file, py_file in UI_FILES:
        if not os.path.exists(ui_file):
            continue
        if (not force) and os.path.exists(py_file) and \
                os.path.getmtime(py_file) >= os.path.getmtime(ui_file):
            continue  # up to date
        subprocess.run(["pyside6-uic", ui_file, "-o", py_file], check=True)
        regenerated = True
    return regenerated


def ensure_ui() -> None:
    """Best-effort auto-regenerate; warn (don't crash) if the tool is missing."""
    try:
        if regen():
            print("[regen_ui] *_ui.py regenerated from ui/*.ui")
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"[regen_ui] warning: pyside6-uic failed ({exc}); "
              f"using the existing *_ui.py if present.")


if __name__ == "__main__":
    regen(force=True)
    print("UI python files generated.")
