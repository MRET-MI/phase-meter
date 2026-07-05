"""
CP-700M コントローラ GUI のエントリポイント（単体起動）。

起動時に regen_ui.ensure_ui() で ui/main_window.ui が更新されていれば
pyside6-uic で ui_main_window.py を再生成する（pyside6-designer で .ui を編集して
再起動するだけで反映される）。

  実行:  python main.py
  依存:  requirements.txt（PySide6 / pyserial）
"""
from __future__ import annotations

from pathlib import Path

import regen_ui
regen_ui.ensure_ui()

from ui.app import main

CONFIG_PATH = Path(__file__).parent / "cp700_config.json"

if __name__ == "__main__":
    main(config_path=CONFIG_PATH)
