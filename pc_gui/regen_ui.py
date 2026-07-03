"""Regenerate ui_main_window.py from ui/main_window.ui via pyside6-uic.

- Standalone:  python regen_ui.py         (force regenerate)
- From main.py: ensure_ui() regenerates only when the .ui is newer than the .py,
  so you can just edit the .ui in pyside6-designer and re-run the app.
"""

from __future__ import annotations

import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
UI_FILE = os.path.join(HERE, "ui", "main_window.ui")
PY_FILE = os.path.join(HERE, "ui_main_window.py")


def regen(force: bool = False) -> bool:
    """Run pyside6-uic if needed. Returns True if it (re)generated the file."""
    if not os.path.exists(UI_FILE):
        return False
    if (not force) and os.path.exists(PY_FILE) and \
            os.path.getmtime(PY_FILE) >= os.path.getmtime(UI_FILE):
        return False  # up to date
    subprocess.run(["pyside6-uic", UI_FILE, "-o", PY_FILE], check=True)
    return True


def ensure_ui() -> None:
    """Best-effort auto-regenerate; warn (don't crash) if the tool is missing."""
    try:
        if regen():
            print("[regen_ui] ui_main_window.py regenerated from main_window.ui")
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"[regen_ui] warning: pyside6-uic failed ({exc}); "
              f"using the existing ui_main_window.py if present.")


if __name__ == "__main__":
    regen(force=True)
    print("ui_main_window.py generated.")
