"""
app.py
CP-700M コントローラの UI ロジック。

レイアウトは ui/main_window.ui（pyside6-designer で編集）に定義し、本ファイルは
objectName でウィジェットを参照してロジックを配線する。3軸の繰り返しグリッドのみ
stageContainer へ実行時に動的挿入する。

- Cp700ControlPanel(QWidget, Ui_MainWindow) : 全操作 UI とロジックを内包（将来 auto-stage-control
  へ import して子ウィンドウ化できるよう QWidget パネルとして分離）。
- Cp700MainWindow(QMainWindow)             : パネルを載せる薄いラッパー（単体起動用）。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtSerialPort import QSerialPortInfo
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QWidget,
)

from comm.transport import MockTransport, SerialTransport, TransportError
from core.config import Cp700Config
from core.controller import Cp700Controller
from ui.settings_dialog import Cp700SettingsDialog

# ui_main_window.py は .ui から pyside6-uic で生成される。無ければ再生成を試みる。
try:
    from ui_main_window import Ui_MainWindow
except ImportError:
    import regen_ui
    regen_ui.regen(force=True)
    from ui_main_window import Ui_MainWindow

_AXES = ("1", "2", "3")


@dataclass
class _AxisRow:
    """1軸分のウィジェット群（mm 表示）。"""
    jog_minus:       QPushButton
    jog_plus:        QPushButton
    dist_spin:       QDoubleSpinBox   # 移動量 [mm]（相対）
    speed_spin:      QDoubleSpinBox   # 移動速度 [mm/s]
    move_button:     QPushButton      # 相対移動
    target_spin:     QDoubleSpinBox   # 目標位置 [mm]（未編集時は現在位置を表示）
    abs_move_button: QPushButton      # 絶対移動
    home_button:     QPushButton      # 原点復帰
    zero_button:     QPushButton      # 0クリア
    exc_button:      QPushButton      # 励磁トグル
    stop_button:     QPushButton      # 停止

    def all_widgets(self) -> list[QWidget]:
        return [
            self.jog_minus, self.jog_plus,
            self.dist_spin, self.speed_spin, self.move_button,
            self.target_spin, self.abs_move_button,
            self.home_button, self.zero_button, self.exc_button, self.stop_button,
        ]


def _make_axis_row() -> _AxisRow:
    minus = QPushButton("−")
    plus_ = QPushButton("＋")

    dist = QDoubleSpinBox()
    dist.setRange(0.0, 1_000.0)
    dist.setSingleStep(0.1)
    dist.setDecimals(3)
    dist.setValue(1.0)
    dist.setSuffix(" mm")

    speed = QDoubleSpinBox()
    speed.setRange(0.001, 1_000.0)
    speed.setSingleStep(1.0)
    speed.setDecimals(3)
    speed.setValue(5.0)
    speed.setSuffix(" mm/s")

    target = QDoubleSpinBox()
    target.setRange(-10_000.0, 10_000.0)
    target.setSingleStep(0.1)
    target.setDecimals(3)
    target.setValue(0.0)
    target.setSuffix(" mm")
    target.setObjectName("targetSpin")

    exc = QPushButton("励磁")
    exc.setCheckable(True)

    stop = QPushButton("停止")
    stop.setObjectName("stopButton")

    return _AxisRow(
        jog_minus=minus,
        jog_plus=plus_,
        dist_spin=dist,
        speed_spin=speed,
        move_button=QPushButton("移動"),
        target_spin=target,
        abs_move_button=QPushButton("絶対移動"),
        home_button=QPushButton("原点"),
        zero_button=QPushButton("0クリア"),
        exc_button=exc,
        stop_button=stop,
    )


class Cp700ControlPanel(QWidget, Ui_MainWindow):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.setupUi(self)

        self.controller:   Cp700Controller | None = None
        self._config_path: Path = config_path
        self._config:      Cp700Config = Cp700Config.load_or_default(config_path)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(300)
        self._poll_timer.timeout.connect(self._poll_status)

        self._rows: dict[str, _AxisRow] = {ax: _make_axis_row() for ax in _AXES}
        self._last_pos_mm: dict[str, float] = {ax: 0.0 for ax in _AXES}

        self._init_widgets()
        self._build_stage_grid()
        self._apply_config_to_widgets()
        self._wire()
        self._apply_style()
        self.mockCheck.setChecked(True)
        self.refresh_ports()
        self._set_connected(False)

    # ── 初期化 ────────────────────────────────────────────────────────────────

    def _init_widgets(self) -> None:
        self.jogSpeedSpin.setRange(0.001, 1_000.0)
        self.jogSpeedSpin.setSingleStep(0.5)
        self.jogSpeedSpin.setDecimals(3)
        self.jogSpeedSpin.setValue(2.0)
        self.jogSpeedSpin.setSuffix(" mm/s")
        self.commandEdit.setPlaceholderText("例: Q:   /   M:1+P5000   /   V:")

    def _apply_config_to_widgets(self) -> None:
        """config の既定速度を各操作欄へ反映（起動時・設定変更後）。"""
        for axis in _AXES:
            cfg = self._axis_cfg(axis)
            spin = self._rows[axis].speed_spin
            spin.blockSignals(True)
            spin.setValue(cfg.move_speed_mm_s)
            spin.blockSignals(False)
        # 共通ジョグ速度は軸1の既定値を採用
        self.jogSpeedSpin.blockSignals(True)
        self.jogSpeedSpin.setValue(self._axis_cfg("1").jog_speed_mm_s)
        self.jogSpeedSpin.blockSignals(False)

    def open_settings(self) -> None:
        dlg = Cp700SettingsDialog(self._config, self._config_path, self.controller, self)
        if dlg.exec():
            self._apply_config_to_widgets()
            self._log("設定を保存しました")

    def _build_stage_grid(self) -> None:
        grid = QGridLayout(self.stageContainer)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        headers = [
            "軸", "ジョグ −", "ジョグ ＋", "移動量 [mm]", "速度 [mm/s]", "移動",
            "目標位置 [mm]", "絶対移動", "原点", "0クリア", "励磁", "停止",
        ]
        for col, text in enumerate(headers):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, col)

        for row_idx, axis in enumerate(_AXES, start=1):
            r = self._rows[axis]
            ax_lbl = QLabel(axis)
            ax_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(ax_lbl,            row_idx, 0)
            grid.addWidget(r.jog_minus,       row_idx, 1)
            grid.addWidget(r.jog_plus,        row_idx, 2)
            grid.addWidget(r.dist_spin,       row_idx, 3)
            grid.addWidget(r.speed_spin,      row_idx, 4)
            grid.addWidget(r.move_button,     row_idx, 5)
            grid.addWidget(r.target_spin,     row_idx, 6)
            grid.addWidget(r.abs_move_button, row_idx, 7)
            grid.addWidget(r.home_button,     row_idx, 8)
            grid.addWidget(r.zero_button,     row_idx, 9)
            grid.addWidget(r.exc_button,      row_idx, 10)
            grid.addWidget(r.stop_button,     row_idx, 11)

        grid.setColumnStretch(3, 2)
        grid.setColumnStretch(4, 2)
        grid.setColumnStretch(6, 2)

    # ── シグナル接続 ──────────────────────────────────────────────────────────

    def _wire(self) -> None:
        self.refreshButton.clicked.connect(self.refresh_ports)
        self.connectButton.clicked.connect(self.connect_stage)
        self.disconnectButton.clicked.connect(self.disconnect_stage)
        self.testButton.clicked.connect(self.test_connection)
        self.sendButton.clicked.connect(self.send_manual_command)
        self.stopAllButton.clicked.connect(self.stop_immediate)
        self.settingsButton.clicked.connect(self.open_settings)

        for axis, r in self._rows.items():
            r.move_button.clicked.connect(lambda _, ax=axis: self._execute_move(ax))
            r.abs_move_button.clicked.connect(lambda _, ax=axis: self._execute_move_absolute(ax))
            r.home_button.clicked.connect(
                lambda _, ax=axis: self._do(lambda c: c.home(ax), f"軸{ax} 原点復帰"))
            r.zero_button.clicked.connect(
                lambda _, ax=axis: self._do(lambda c: c.counter_clear(ax), f"軸{ax} 座標0クリア"))
            r.stop_button.clicked.connect(
                lambda _, ax=axis: self._do(lambda c: c.stop(ax), f"軸{ax} 停止"))
            r.exc_button.toggled.connect(
                lambda checked, ax=axis: self._do(
                    lambda c: c.set_excitation(ax, checked),
                    f"軸{ax} 励磁{'ON' if checked else 'OFF'}"))
            r.jog_minus.pressed.connect(lambda ax=axis: self._jog_start(ax, positive=False))
            r.jog_minus.released.connect(lambda ax=axis: self._jog_stop(ax))
            r.jog_plus.pressed.connect(lambda ax=axis: self._jog_start(ax, positive=True))
            r.jog_plus.released.connect(lambda ax=axis: self._jog_stop(ax))

    # ── 接続 ──────────────────────────────────────────────────────────────────

    def refresh_ports(self) -> None:
        current = self.portCombo.currentText()
        self.portCombo.clear()
        ports = [p.portName() for p in QSerialPortInfo.availablePorts()]
        self.portCombo.addItems(ports)
        if current in ports:
            self.portCombo.setCurrentText(current)
        self._log(f"検出ポート: {', '.join(ports) if ports else 'なし'}")

    def connect_stage(self) -> None:
        try:
            if self.mockCheck.isChecked():
                transport = MockTransport()
            else:
                port = self.portCombo.currentText().strip()
                if not port:
                    QMessageBox.warning(self, "接続できません", "シリアルポートを選択してください。")
                    return
                transport = SerialTransport(port=port)
            self.controller = Cp700Controller(transport)
            self.controller.connect()
        except TransportError as exc:
            QMessageBox.critical(self, "通信エラー", str(exc))
            self._log(f"ERROR {exc}")
            return

        self._set_connected(True)
        self._log("接続しました")
        # 接続直後に V: で疎通確認（COMM RES 非依存で必ず応答が返る）
        self._verify_link()

    def disconnect_stage(self) -> None:
        if self.controller is not None:
            self.controller.disconnect()
        self.controller = None
        self._set_connected(False)
        self._log("切断しました")

    def test_connection(self) -> None:
        if not self._require_connection():
            return
        self._verify_link()

    def _verify_link(self) -> None:
        try:
            resp = self.controller.version()
        except TransportError as exc:
            self._log(f"ERROR {exc}")
            QMessageBox.critical(self, "接続テスト失敗", str(exc))
            return
        if resp and resp != "NO RESPONSE":
            self._log(f"接続テスト成功: バージョン {resp}")
        else:
            self._log("接続テスト: 応答なし（電源・ドライバ・ポートを確認してください）")
            QMessageBox.warning(
                self, "接続テスト",
                "CP-700M から応答がありません。\n電源・USBドライバ・ポート選択を確認してください。")

    # ── 移動（mm → pulse 換算） ────────────────────────────────────────────────

    def _axis_cfg(self, axis: str):
        return self._config.axes[axis]

    def _speeds_for(self, cfg, r):
        """行の移動速度から (move_pps, start_pps) を作る（最高速度でクランプ、自起動速度を初速に）。"""
        spd = min(r.speed_spin.value(), cfg.max_speed_mm_s)
        move_pps  = cfg.mmps_to_pps(spd)
        start_pps = cfg.mmps_to_pps(min(cfg.start_speed_mm_s, spd))
        return move_pps, start_pps

    def _execute_move(self, axis: str) -> None:
        cfg = self._axis_cfg(axis)
        if cfg.mm_per_pulse == 0.0:
            QMessageBox.warning(self, "設定エラー", f"軸{axis} の mm/pulse が 0 です。設定を確認してください。")
            return
        r = self._rows[axis]
        dist = r.dist_spin.value()
        signed = -dist if cfg.invert else dist   # GUI 論理反転
        target_mm = self._last_pos_mm.get(axis, 0.0) + signed
        if not cfg.within_soft_limit(target_mm):
            QMessageBox.warning(self, "ソフトリミット",
                                f"軸{axis} の目標 {target_mm:.3f} mm がソフトリミット範囲外です。")
            return
        pulses = cfg.mm_to_pulses(signed)
        if pulses == 0:
            return
        move_pps, start_pps = self._speeds_for(cfg, r)
        self._do(
            lambda c: c.move_relative_and_go(axis, pulses, start_pps=start_pps,
                                             max_pps=move_pps, accel_ms=cfg.accel_ms),
            f"軸{axis} 相対移動 {signed:+.3f} mm ({pulses} pulse)")

    def _execute_move_absolute(self, axis: str) -> None:
        cfg = self._axis_cfg(axis)
        if cfg.mm_per_pulse == 0.0:
            QMessageBox.warning(self, "設定エラー", f"軸{axis} の mm/pulse が 0 です。設定を確認してください。")
            return
        r = self._rows[axis]
        target_mm = r.target_spin.value()   # 絶対座標（invert は無関係）
        if not cfg.within_soft_limit(target_mm):
            QMessageBox.warning(self, "ソフトリミット",
                                f"軸{axis} の目標 {target_mm:.3f} mm がソフトリミット範囲外です。")
            return
        pulses = cfg.mm_to_pulses(target_mm)
        move_pps, start_pps = self._speeds_for(cfg, r)
        self._do(
            lambda c: c.move_absolute_and_go(axis, pulses, start_pps=start_pps,
                                             max_pps=move_pps, accel_ms=cfg.accel_ms),
            f"軸{axis} 絶対移動 {target_mm:.3f} mm ({pulses} pulse)")

    # ── ジョグ ────────────────────────────────────────────────────────────────

    def _jog_start(self, axis: str, positive: bool) -> None:
        if not self._is_connected():
            return
        cfg = self._axis_cfg(axis)
        pps = cfg.mmps_to_pps(min(self.jogSpeedSpin.value(), cfg.max_speed_mm_s))
        stage_positive = positive if not cfg.invert else (not positive)   # GUI 論理反転
        try:
            self.controller.jog_start(axis, stage_positive, pps=pps, accel_ms=cfg.accel_ms)
            self._log(f"軸{axis} ジョグ{'＋' if positive else '−'}開始")
        except TransportError as exc:
            self._log(f"ERROR {exc}")

    def _jog_stop(self, axis: str) -> None:
        if not self._is_connected():
            return
        try:
            self.controller.jog_stop(axis)
            self._log(f"軸{axis} ジョグ停止")
        except TransportError as exc:
            self._log(f"ERROR {exc}")

    # ── 全軸即停止 ────────────────────────────────────────────────────────────

    def stop_immediate(self) -> None:
        self._do(lambda c: c.stop_immediate(), "全軸即停止 (L:E)")

    # ── ポーリング（Q: で 3軸位置＋状態） ────────────────────────────────────────

    def _poll_status(self) -> None:
        if not self._is_connected():
            return
        try:
            st = self.controller.query_status()
        except (TransportError, ValueError):
            return

        for i, axis in enumerate(_AXES):
            mm = self._axis_cfg(axis).pulses_to_mm(st.positions[i])
            self._last_pos_mm[axis] = mm   # 相対移動のソフトリミット判定に使用
            spin = self._rows[axis].target_spin
            if not spin.hasFocus():
                spin.blockSignals(True)
                spin.setValue(mm)
                spin.blockSignals(False)

        self._update_status_labels(st)

    def _update_status_labels(self, st) -> None:
        accept_txt = {"R": "全コマンド受付可", "B": "一部受付", "I": "インターロック中"}.get(st.state, st.state or "-")
        self.stateLabel.setText(f"受付状態: {accept_txt}")

        if st.interlocked:
            self.interlockLabel.setText("インターロック: 中")
            self.interlockLabel.setStyleSheet("color: #b42318; font-weight: 700;")
        else:
            self.interlockLabel.setText("インターロック: 正常")
            self.interlockLabel.setStyleSheet("color: #067647;")

        limit_axes = [ax for i, ax in enumerate(_AXES) if st.limit_on(i)]
        if limit_axes:
            self.limitLabel.setText("リミット: 軸 " + ",".join(limit_axes))
            self.limitLabel.setStyleSheet("color: #b42318; font-weight: 700;")
        else:
            self.limitLabel.setText("リミット: 正常")
            self.limitLabel.setStyleSheet("color: #067647;")

    # ── 直接コマンド ──────────────────────────────────────────────────────────

    def send_manual_command(self) -> None:
        if not self._require_connection():
            return
        command = self.commandEdit.toPlainText().strip()
        if not command:
            return
        try:
            resp = self.controller.send_raw(command, expect_response=True)
        except TransportError as exc:
            QMessageBox.critical(self, "通信エラー", str(exc))
            self._log(f"ERROR {exc}")
            return
        self._log(f"> {command}")
        if resp:
            self._log(f"< {resp}")

    # ── 実行ヘルパー ──────────────────────────────────────────────────────────

    def _do(self, action, description: str) -> None:
        """駆動/設定系コマンド（応答なし）を送信し、操作内容をログする。"""
        if not self._require_connection():
            return
        try:
            action(self.controller)
        except TransportError as exc:
            QMessageBox.critical(self, "通信エラー", str(exc))
            self._log(f"ERROR {exc}")
            return
        self._log(description)

    def _is_connected(self) -> bool:
        return self.controller is not None and self.controller.is_connected()

    def _require_connection(self) -> bool:
        if not self._is_connected():
            QMessageBox.warning(self, "未接続", "先にコントローラへ接続してください。")
            return False
        return True

    # ── 状態管理 ──────────────────────────────────────────────────────────────

    def _set_connected(self, connected: bool) -> None:
        self.settingsButton.setEnabled(True)   # 設定編集は接続前後どちらでも可
        self.connectButton.setEnabled(not connected)
        self.disconnectButton.setEnabled(connected)
        self.refreshButton.setEnabled(not connected)
        self.portCombo.setEnabled(not connected)
        self.mockCheck.setEnabled(not connected)
        self.testButton.setEnabled(connected)
        self.sendButton.setEnabled(connected)
        self.stopAllButton.setEnabled(connected)
        self.jogSpeedSpin.setEnabled(connected)
        for r in self._rows.values():
            for w in r.all_widgets():
                w.setEnabled(connected)

        if connected:
            self._poll_timer.start()
        else:
            self._poll_timer.stop()
            self.stateLabel.setText("未接続")
            self.interlockLabel.setText("インターロック: -")
            self.interlockLabel.setStyleSheet("")
            self.limitLabel.setText("リミット: -")
            self.limitLabel.setStyleSheet("")
            for r in self._rows.values():
                r.target_spin.blockSignals(True)
                r.target_spin.setValue(0.0)
                r.target_spin.blockSignals(False)

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logEdit.appendPlainText(f"[{timestamp}] {message}")

    # ── スタイル ──────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QWidget { background: #f5f7fb; }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d9dee8;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                min-height: 28px;
                min-width: 52px;
                padding: 2px 6px;
            }
            QPushButton#stopButton, QPushButton#stopAllButton {
                background: #b42318;
                color: white;
                font-weight: 700;
            }
            QPushButton:checked {
                background: #175cd3;
                color: white;
            }
            QDoubleSpinBox#targetSpin {
                font-family: Consolas, monospace;
                font-weight: 600;
                background: #eef2f9;
            }
            QPlainTextEdit {
                font-family: Consolas, monospace;
                font-size: 10pt;
            }
            QLabel { font-size: 9pt; }
        """)


class Cp700MainWindow(QMainWindow):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.setWindowTitle("CP-700M コントローラ")
        self.resize(1160, 640)
        self.panel = Cp700ControlPanel(config_path)
        self.setCentralWidget(self.panel)


def main(config_path: Path | None = None) -> None:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "cp700_config.json"
    app = QApplication(sys.argv)
    window = Cp700MainWindow(config_path=config_path)
    window.show()
    sys.exit(app.exec())
