"""
settings_dialog.py
CP-700M 軸設定ダイアログ。

軸ごとのネジリード・分割数・速度（自起動/最高/既定移動/既定ジョグ）・加減速時間・
ソフトリミット・方向反転を編集して JSON 保存する。任意で CP-700M 本体パラメータへ
（F:M コマンドで）書き込む。auto-stage-control の StageSettingsDialog と同じ流儀。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import AXES, DIVIDE_OPTIONS, AxisConfig, Cp700Config

if TYPE_CHECKING:
    from core.controller import Cp700Controller


class _AxisWidget(QWidget):
    """1軸分の設定フォーム。"""

    def __init__(self, cfg: AxisConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build(cfg)

    def _dspin(self, lo, hi, step, suffix, value, decimals=3) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setSingleStep(step)
        w.setDecimals(decimals)
        w.setSuffix(suffix)
        w.setValue(value)
        return w

    def _build(self, cfg: AxisConfig) -> None:
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setContentsMargins(12, 12, 12, 12)
        form.setVerticalSpacing(8)

        self.lead = self._dspin(0.001, 50.0, 0.1, " mm", cfg.lead_mm, 3)
        form.addRow("ネジリード", self.lead)

        self.divide = QComboBox()
        for d in DIVIDE_OPTIONS:
            self.divide.addItem(str(d), float(d))
        self._select_divide(cfg.divide)
        form.addRow("分割数", self.divide)

        self.mpp_label = QLabel()
        self.lead.valueChanged.connect(self._update_mpp)
        self.divide.currentIndexChanged.connect(self._update_mpp)
        form.addRow("→ mm/pulse", self.mpp_label)

        self.max_speed   = self._dspin(0.001, 1000.0, 1.0, " mm/s", cfg.max_speed_mm_s, 3)
        self.start_speed = self._dspin(0.001, 1000.0, 0.5, " mm/s", cfg.start_speed_mm_s, 3)
        self.move_speed  = self._dspin(0.001, 1000.0, 1.0, " mm/s", cfg.move_speed_mm_s, 3)
        self.jog_speed   = self._dspin(0.001, 1000.0, 0.5, " mm/s", cfg.jog_speed_mm_s, 3)
        form.addRow("最高速度", self.max_speed)
        form.addRow("自起動速度", self.start_speed)
        form.addRow("既定移動速度", self.move_speed)
        form.addRow("既定ジョグ速度", self.jog_speed)

        self.accel = QSpinBox()
        self.accel.setRange(0, 1000)
        self.accel.setSingleStep(10)
        self.accel.setSuffix(" ms")
        self.accel.setValue(int(cfg.accel_ms))
        form.addRow("加減速時間", self.accel)

        self.slimit_cw  = self._dspin(0.0, 10_000.0, 1.0, " mm", cfg.soft_limit_cw_mm, 3)
        self.slimit_ccw = self._dspin(0.0, 10_000.0, 1.0, " mm", cfg.soft_limit_ccw_mm, 3)
        form.addRow("＋方向ソフトリミット (0=無効)", self.slimit_cw)
        form.addRow("−方向ソフトリミット (0=無効)", self.slimit_ccw)

        self.invert = QCheckBox("＋/− を反転する")
        self.invert.setChecked(bool(cfg.invert))
        form.addRow("方向反転", self.invert)

        self._update_mpp()

    def _select_divide(self, value) -> None:
        idx = self.divide.findData(float(value))
        if idx < 0:
            idx = self.divide.findData(20.0)
        self.divide.setCurrentIndex(idx if idx >= 0 else 0)

    def _update_mpp(self) -> None:
        lead = self.lead.value()
        div = self.divide.currentData() or 0.0
        mpp = lead / (500.0 * div) if div else 0.0
        self.mpp_label.setText(f"{mpp:.6g} mm/pulse")

    def to_axis_config(self) -> AxisConfig:
        return AxisConfig(
            lead_mm           = self.lead.value(),
            divide            = float(self.divide.currentData()),
            start_speed_mm_s  = self.start_speed.value(),
            jog_speed_mm_s    = self.jog_speed.value(),
            move_speed_mm_s   = self.move_speed.value(),
            max_speed_mm_s    = self.max_speed.value(),
            accel_ms          = self.accel.value(),
            soft_limit_cw_mm  = self.slimit_cw.value(),
            soft_limit_ccw_mm = self.slimit_ccw.value(),
            invert            = self.invert.isChecked(),
        )

    def load_from_axis_config(self, cfg: AxisConfig) -> None:
        self.lead.setValue(cfg.lead_mm)
        self._select_divide(cfg.divide)
        self.start_speed.setValue(cfg.start_speed_mm_s)
        self.jog_speed.setValue(cfg.jog_speed_mm_s)
        self.move_speed.setValue(cfg.move_speed_mm_s)
        self.max_speed.setValue(cfg.max_speed_mm_s)
        self.accel.setValue(int(cfg.accel_ms))
        self.slimit_cw.setValue(cfg.soft_limit_cw_mm)
        self.slimit_ccw.setValue(cfg.soft_limit_ccw_mm)
        self.invert.setChecked(bool(cfg.invert))


class Cp700SettingsDialog(QDialog):
    """CP-700M 軸設定ダイアログ。"""

    def __init__(
        self,
        config: Cp700Config,
        config_path: Path,
        controller: "Cp700Controller | None",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("CP-700M 軸設定")
        self.setMinimumWidth(460)
        self._config = config
        self._config_path = config_path
        self._controller = controller
        self._axis_widgets: dict[str, _AxisWidget] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        tabs = QTabWidget()
        for ax in AXES:
            w = _AxisWidget(self._config.axes[ax])
            self._axis_widgets[ax] = w
            tabs.addTab(w, f"軸 {ax}")
        root.addWidget(tabs)

        row = QHBoxLayout()
        copy_btn = QPushButton("軸1の設定を全軸へコピー")
        copy_btn.clicked.connect(self._copy_axis1)
        row.addWidget(copy_btn)
        self._write_btn = QPushButton("本体へ書き込み (F:M)")
        self._write_btn.clicked.connect(self._write_to_device)
        row.addWidget(self._write_btn)
        row.addStretch()
        root.addLayout(row)
        if self._controller is None or not self._controller.is_connected():
            self._write_btn.setEnabled(False)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ── 内部処理 ──────────────────────────────────────────────────────────────

    def _copy_axis1(self) -> None:
        src = self._axis_widgets["1"].to_axis_config()
        for ax in AXES:
            if ax != "1":
                self._axis_widgets[ax].load_from_axis_config(src)

    def _collect(self) -> None:
        for ax, w in self._axis_widgets.items():
            self._config.axes[ax] = w.to_axis_config()

    def _accept(self) -> None:
        self._collect()
        try:
            self._config.save(self._config_path)
        except Exception as exc:
            QMessageBox.warning(self, "保存エラー", f"設定ファイルの保存に失敗しました:\n{exc}")
        self.accept()

    def _write_to_device(self) -> None:
        if self._controller is None:
            return
        self._collect()
        try:
            for ax in AXES:
                self._controller.write_axis_params(ax, self._config.axes[ax])
        except Exception as exc:
            QMessageBox.critical(self, "エラー", f"本体への書き込みに失敗しました:\n{exc}")
            return
        QMessageBox.information(
            self, "完了",
            "本体パラメータへ書き込みを送信しました。\n"
            "（COMM RES=OFF のため成否応答は取得していません。方向反転は GUI 内部設定のため本体には書き込みません。）")
