"""
trigger_dialog.py
CP-700M トリガ出力設定ダイアログ。

背面 TRG コネクタからのトリガ信号出力を設定する（マニュアル §5.2.15 / §4.4）。
- 本体パラメータ: TRG LEV(HI/LO), TRG WIDTH[µs]（F:M2 / F:M3）
- 出力モード:
    禁止           T:S
    周期タイマ     T:T<ms>
    移動パルス同期 T:P<axis>P<pulses>
    定速域パルス   T:<axis>TP<pulses>
    位置到達       T:<axis>±P<abs>（駆動コマンド発行前に設定）
- 単発出力       T:M
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.config import AXES, Cp700Config

if TYPE_CHECKING:
    from core.controller import Cp700Controller


class Cp700TriggerDialog(QDialog):
    # (表示ラベル, 内部キー)
    MODES = [
        ("禁止 (T:S)",             "stop"),
        ("周期タイマ (T:T)",       "timer"),
        ("移動パルス同期 (T:P)",   "pulse"),
        ("定速域パルス (T:<軸>TP)", "constspeed"),
        ("位置到達 (T:<軸>±P)",    "position"),
    ]

    def __init__(
        self,
        config: Cp700Config,
        controller: "Cp700Controller | None",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("CP-700M トリガ出力設定")
        self.setMinimumWidth(440)
        self._config = config
        self._controller = controller
        self._build_ui()
        self._update_mode_ui()
        if controller is None or not controller.is_connected():
            self._set_send_enabled(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # ── 本体パラメータ（TRG LEV / WIDTH） ──
        pgroup = QGroupBox("トリガ信号（本体パラメータ）")
        pform = QFormLayout(pgroup)
        self.lev_combo = QComboBox()
        self.lev_combo.addItem("HI（非出力時 H）", "HI")
        self.lev_combo.addItem("LO（非出力時 L）", "LO")
        pform.addRow("TRG LEV", self.lev_combo)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 100_000)
        self.width_spin.setSuffix(" µs")
        self.width_spin.setValue(10)
        pform.addRow("TRG WIDTH", self.width_spin)
        self.write_param_btn = QPushButton("レベル/幅を本体へ書込 (F:M2/F:M3)")
        self.write_param_btn.clicked.connect(self._write_params)
        pform.addRow(self.write_param_btn)
        root.addWidget(pgroup)

        # ── 出力モード ──
        mgroup = QGroupBox("トリガ出力モード")
        mform = QFormLayout(mgroup)
        self.mode_combo = QComboBox()
        for label, _key in self.MODES:
            self.mode_combo.addItem(label)
        self.mode_combo.currentIndexChanged.connect(self._update_mode_ui)
        mform.addRow("モード", self.mode_combo)

        self.axis_combo = QComboBox()
        for ax in AXES:
            self.axis_combo.addItem(f"軸 {ax}", ax)
        mform.addRow("軸", self.axis_combo)

        self.period_spin = QSpinBox()
        self.period_spin.setRange(1, 100_000)
        self.period_spin.setSuffix(" ms")
        self.period_spin.setValue(100)
        mform.addRow("周期", self.period_spin)

        self.pulse_spin = QSpinBox()
        self.pulse_spin.setRange(1, 1_000_000)
        self.pulse_spin.setSuffix(" pulse")
        self.pulse_spin.setValue(1000)
        mform.addRow("パルス間隔", self.pulse_spin)

        self.pos_spin = QDoubleSpinBox()
        self.pos_spin.setRange(-10_000.0, 10_000.0)
        self.pos_spin.setDecimals(3)
        self.pos_spin.setSuffix(" mm")
        mform.addRow("位置（絶対）", self.pos_spin)

        self.apply_btn = QPushButton("適用")
        self.apply_btn.clicked.connect(self._apply_mode)
        mform.addRow(self.apply_btn)
        root.addWidget(mgroup)

        # ── 即時操作 / 閉じる ──
        row = QHBoxLayout()
        self.oneshot_btn = QPushButton("単発出力 (T:M)")
        self.oneshot_btn.clicked.connect(self._oneshot)
        self.stop_btn = QPushButton("トリガ停止 (T:S)")
        self.stop_btn.clicked.connect(self._stop)
        row.addWidget(self.oneshot_btn)
        row.addWidget(self.stop_btn)
        row.addStretch()
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        root.addLayout(row)

        note = QLabel(
            "・トリガ論理/パルス幅は「本体へ書込」後に有効（必要ならフラッシュ保存）。\n"
            "・位置到達モードは「適用」後にダイアログを閉じ、メイン画面で絶対移動を実行"
            "してください（駆動前の設定が有効）。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #555;")
        root.addWidget(note)

    # ── 内部処理 ──────────────────────────────────────────────────────────────

    def _set_send_enabled(self, on: bool) -> None:
        for w in (self.write_param_btn, self.apply_btn, self.oneshot_btn, self.stop_btn):
            w.setEnabled(on)

    def _update_mode_ui(self) -> None:
        key = self.MODES[self.mode_combo.currentIndex()][1]
        self.axis_combo.setEnabled(key in ("pulse", "constspeed", "position"))
        self.period_spin.setEnabled(key == "timer")
        self.pulse_spin.setEnabled(key in ("pulse", "constspeed"))
        self.pos_spin.setEnabled(key == "position")

    def _require(self) -> bool:
        if self._controller is None or not self._controller.is_connected():
            QMessageBox.warning(self, "未接続", "先にコントローラへ接続してください。")
            return False
        return True

    def _write_params(self) -> None:
        if not self._require():
            return
        try:
            self._controller.write_trigger_params(
                self.lev_combo.currentData(), self.width_spin.value())
        except Exception as exc:
            QMessageBox.critical(self, "エラー", str(exc))
            return
        QMessageBox.information(self, "完了", "TRG LEV / WIDTH を本体へ送信しました。")

    def _apply_mode(self) -> None:
        if not self._require():
            return
        key = self.MODES[self.mode_combo.currentIndex()][1]
        c = self._controller
        axis = self.axis_combo.currentData()
        try:
            if key == "stop":
                c.trigger_stop()
            elif key == "timer":
                c.trigger_timer(self.period_spin.value())
            elif key == "pulse":
                c.trigger_pulse(axis, self.pulse_spin.value())
            elif key == "constspeed":
                c.trigger_constspeed(axis, self.pulse_spin.value())
            elif key == "position":
                pulses = self._config.axes[axis].mm_to_pulses(self.pos_spin.value())
                c.trigger_position(axis, pulses)
        except Exception as exc:
            QMessageBox.critical(self, "エラー", str(exc))

    def _oneshot(self) -> None:
        if self._require():
            try:
                self._controller.trigger_oneshot()
            except Exception as exc:
                QMessageBox.critical(self, "エラー", str(exc))

    def _stop(self) -> None:
        if self._require():
            try:
                self._controller.trigger_stop()
            except Exception as exc:
                QMessageBox.critical(self, "エラー", str(exc))
