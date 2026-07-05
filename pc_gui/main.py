"""phase-meter GUI controller.

Layout lives in ui/main_window.ui (edit with pyside6-designer). This file only
wires logic to the widgets (referenced by objectName) and handles serial I/O.

Run:  python main.py     (auto-regenerates ui_main_window.py if the .ui changed)
Deps: see requirements.txt
"""

from __future__ import annotations

import csv
import os
import re
import sys
import time
from datetime import datetime

import regen_ui
regen_ui.ensure_ui()

from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QWidget,
)

from serial_worker import SerialWorker, available_ports
from script_runner import ScriptRunner, expand_script

try:
    from ui_main_window import Ui_MainWindow
    from ui_settings_dialog import Ui_SettingsDialog
except ImportError:
    sys.exit("UI python files missing. Generate them with:\n"
             "    python regen_ui.py")


class SettingsDialog(QDialog, Ui_SettingsDialog):
    """位相計算パラメータの設定サブウィンドウ（Designer: ui/settings_dialog.ui）。

    ウィジェットのみを保持し、送受信ロジックの配線は MainWindow 側で行う。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

# Firmware calc/output rate (TIM6 = 100 Hz). Each seq is one 10 ms tick.
SAMPLE_PERIOD_S = 0.01


class MainWindow(QWidget, Ui_MainWindow):
    # "RA" register-dump line: "<addr>:<name>:<unit>:<val>"
    _RA_RE = re.compile(r"^(\d+):([^:]*):(\d+):(-?\d+(?:\.\d+)?)$")
    # An "R<addr>S<val>" set command (to keep the param snapshot in sync)
    _RSET_RE = re.compile(r"^R(\d+)S(.+)$")

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self._settings = SettingsDialog(self)   # 設定はサブウィンドウ

        self._worker: SerialWorker | None = None
        self._csv_writer: csv.writer | None = None
        self._csv_file = None
        self._t0 = time.monotonic()
        self._seq0: int | None = None
        self._history: list[tuple[float, float, float, float]] = []
        self._temp_history: list[tuple[float, float, float, float]] = []

        # 自動計測スクリプト
        self._runner = ScriptRunner(self)
        self._script_text: str | None = None
        self._out_dir: str | None = None
        self._params: dict[int, list] = {}   # addr -> [name, value_str]

        self._init_widgets()
        self._wire()
        self._refresh_ports()
        self._set_connected(False)
        self._set_script_running(False)

    # ── setup ────────────────────────────────────────────────────────────
    def _init_widgets(self) -> None:
        s = self._settings   # 位相計算パラメータはサブウィンドウ側のウィジェット
        for n in (256, 512, 1024, 2048, 4096):
            s.adcNumCombo.addItem(str(n), n)
        s.adcNumCombo.setCurrentText("4096")
        s.peakCombo.addItem("Fixed bin", 0)
        s.peakCombo.addItem("Peak search", 1)
        s.peakCombo.setCurrentIndex(1)
        s.fsSpin.setGroupSeparatorShown(True)
        s.targetSpin.setGroupSeparatorShown(True)

        self.modeCombo.addItem("Free run", 0)          # STOP まで無限
        self.modeCombo.addItem("Fixed duration", 1)    # 秒で指定
        self.modeCombo.addItem("Fixed count", 2)       # データ点数で直接指定
        self.modeCombo.currentIndexChanged.connect(self._update_mode_ui)
        self._update_mode_ui()

        self.phasePlot.configure(ylabel="Phase difference", yunits="deg",
                                 yrange=(-180, 180), color="#1565c0")
        self.ampPlot.configure(ylabel="Peak amplitude", yunits="V",
                               yrange=None, color="#c62828")
        self.tempPlot.configure_multi(
            [("T1", "#1565c0"), ("T2", "#c62828"), ("T3", "#2e7d32")],
            ylabel="Temperature", yunits="°C", yrange=None, legend=True)

        # firmware register address -> widget (dac_v at 10 is a float register)
        self._reg_widgets = {
            1: s.adcNumCombo,
            2: s.fsSpin,
            3: s.targetSpin,
            4: s.searchWinSpin,
            5: s.bandWSpin,
            6: s.maxOffsetSpin,
            9: s.peakCombo,
            10: self.dacSpin,
        }

    def _wire(self) -> None:
        self.refreshButton.clicked.connect(self._refresh_ports)
        self.connectButton.clicked.connect(self._toggle_connect)
        self.runButton.clicked.connect(self._on_run)
        self.stopButton.clicked.connect(lambda: self._send("STOP"))
        self.verButton.clicked.connect(lambda: self._send("VER"))
        self.txSetButton.clicked.connect(lambda: self._send(f"ATTT{self.txSpin.value():.1f}"))
        self.rxSetButton.clicked.connect(lambda: self._send(f"ATTR{self.rxSpin.value():.1f}"))
        self.dacSetButton.clicked.connect(lambda: self._send(f"R10S{self.dacSpin.value():.3f}"))
        self.settingsButton.clicked.connect(self._open_settings)
        self._settings.readButton.clicked.connect(self._settings_read)
        self._settings.applyButton.clicked.connect(self._settings_apply)
        self._settings.saveFlashButton.clicked.connect(lambda: self._send("RS"))
        self.sendButton.clicked.connect(self._send_manual)
        self.cmdEdit.returnPressed.connect(self._send_manual)
        self.saveDataButton.clicked.connect(self._save_history)
        self.csvButton.clicked.connect(self._toggle_csv)
        self.clearButton.clicked.connect(self._clear_plots)

        # 自動計測スクリプト
        self.loadScriptButton.clicked.connect(self._load_script)
        self.runScriptButton.clicked.connect(self._run_script)
        self.stopScriptButton.clicked.connect(self._runner.stop)
        self._runner.send_command.connect(self._send)
        self._runner.request_clear.connect(self._clear_plots)
        self._runner.request_save.connect(self._save_point)
        self._runner.progress.connect(self._on_script_progress)
        self._runner.finished.connect(self._on_script_finished)
        self._runner.failed.connect(self._on_script_failed)

    # ── connection ───────────────────────────────────────────────────────
    def _refresh_ports(self) -> None:
        self.portCombo.clear()
        for device, desc in available_ports():
            self.portCombo.addItem(f"{device} — {desc}", device)
        if self.portCombo.count() == 0:
            self.portCombo.addItem("(no ports found)", None)

    def _toggle_connect(self) -> None:
        if self._worker is None:
            device = self.portCombo.currentData()
            if not device:
                self._append_log("No port selected.")
                return
            worker = SerialWorker(device)
            worker.sample_received.connect(self._on_sample)
            worker.temp_received.connect(self._on_temp)
            worker.line_received.connect(self._on_line)
            worker.error.connect(self._on_error)
            if not worker.open():
                return
            worker.start()
            self._worker = worker
            self._history.clear()
            self._temp_history.clear()
            self._seq0 = None
            self._set_connected(True)
            self._append_log(f"Connected to {device}")
        else:
            self._send("STOP")
            self._worker.stop()
            self._worker = None
            self._set_connected(False)
            self._append_log("Disconnected")

    def _set_connected(self, on: bool) -> None:
        self.connectButton.setText("Disconnect" if on else "Connect")
        self.portCombo.setEnabled(not on)
        self.refreshButton.setEnabled(not on)
        for w in (self.runButton, self.stopButton, self.verButton):
            w.setEnabled(on)
        # スクリプト実行は「接続済み かつ ロード済み」のときのみ
        self.runScriptButton.setEnabled(on and self._script_text is not None)

    # ── events ───────────────────────────────────────────────────────────
    def _send(self, cmd: str) -> None:
        if self._worker is None:
            self._append_log("Not connected.")
            return
        self._worker.send(cmd)
        self._append_log(f"> {cmd}")
        # パラメータ・スナップショットを R<addr>S<val> で更新（保存ヘッダ用）
        m = self._RSET_RE.match(cmd.strip())
        if m:
            addr = int(m.group(1))
            val = m.group(2).strip()
            if addr in self._params:
                self._params[addr][1] = val
            else:
                self._params[addr] = [f"reg{addr}", val]

    def _send_manual(self) -> None:
        txt = self.cmdEdit.text().strip()
        if txt:
            self._send(txt)
            self.cmdEdit.clear()

    def _open_settings(self) -> None:
        # モードレス表示（メインのライブ表示を止めずに設定を触れる）
        self._settings.show()
        self._settings.raise_()
        self._settings.activateWindow()

    def _update_mode_ui(self) -> None:
        # 各スピンは該当モードのときだけ有効化
        mode = self.modeCombo.currentData()
        self.durationSpin.setEnabled(mode == 1)   # Fixed duration
        self.countSpin.setEnabled(mode == 2)      # Fixed count

    def _on_run(self) -> None:
        # 再開時は必ずデータをクリア（全モード共通）
        self._clear_plots()
        mode = self.modeCombo.currentData()
        if mode == 1:                                 # Fixed duration（秒 → 点数）
            n = max(1, round(self.durationSpin.value() / SAMPLE_PERIOD_S))
            self._send(f"RUNN{n}")
        elif mode == 2:                               # Fixed count（点数を直接指定）
            self._send(f"RUNN{self.countSpin.value()}")
        else:                                         # Free run
            self._send("RUN")

    def _on_sample(self, seq: int, deg: float, amp: float, freq: float) -> None:
        if self._seq0 is None:
            self._seq0 = seq
        t = (seq - self._seq0) * SAMPLE_PERIOD_S   # exact, jitter-free time axis
        self.valueLabel.setText(f"phase: {deg:+.3f}°")
        self.freqLabel.setText(f"peak freq: {freq:,.1f} Hz    amp: {amp * 1000.0:.3f} mV")
        self.phasePlot.add(t, deg)
        self.ampPlot.add(t, amp)
        self._history.append((t, deg, amp, freq))
        if self._csv_writer is not None:
            self._csv_writer.writerow(
                [f"{t:.4f}", f"{deg:.3f}", f"{amp:.6f}", f"{freq:.1f}", "", "", ""])

    def _on_temp(self, tick: int, t1: float, t2: float, t3: float) -> None:
        # Same time base as F: tick and seq both come from the 100 Hz dbg_tick.
        if self._seq0 is None:
            self._seq0 = tick
        t = (tick - self._seq0) * SAMPLE_PERIOD_S
        self.tempPlot.add_curve(0, t, t1)
        self.tempPlot.add_curve(1, t, t2)
        self.tempPlot.add_curve(2, t, t3)
        self._temp_history.append((t, t1, t2, t3))
        if self._csv_writer is not None:
            self._csv_writer.writerow(
                [f"{t:.4f}", "", "", "", f"{t1:.3f}", f"{t2:.3f}", f"{t3:.3f}"])

    def _on_line(self, line: str) -> None:
        self._append_log(line)
        if line == "DONE" and not self._runner.running:
            # 手動の時間指定取得の完了通知（スクリプト実行中はランナーが処理）
            self._append_log(f"取得完了: {len(self._history)} サンプル")
        m = self._RA_RE.match(line)
        if m:
            addr, name, val = int(m.group(1)), m.group(2), m.group(4)
            self._params[addr] = [name, val]          # 保存ヘッダ用スナップショット
            w = self._reg_widgets.get(addr)
            if w is not None:
                self._set_reg_widget(w, val)
        # スクリプト・ランナーへ応答行を転送（OK/NG/END/DONE で次ステップへ）
        self._runner.on_line(line)

    def _on_error(self, msg: str) -> None:
        self._append_log(f"[error] {msg}")

    def _append_log(self, text: str) -> None:
        self.logEdit.appendPlainText(text)

    # ── settings ─────────────────────────────────────────────────────────
    def _settings_read(self) -> None:
        self._send("RA")   # device dumps all registers; _on_line updates fields

    def _settings_apply(self) -> None:
        for addr, w in self._reg_widgets.items():
            if isinstance(w, QComboBox):
                s = str(int(w.currentData()))
            elif isinstance(w, QDoubleSpinBox):
                s = f"{w.value():.3f}"            # float register (e.g. dac_v)
            else:
                s = str(int(w.value()))
            self._send(f"R{addr}S{s}")

    @staticmethod
    def _set_reg_widget(w, val_str: str) -> None:
        try:
            fv = float(val_str)
        except ValueError:
            return
        if isinstance(w, QComboBox):
            idx = w.findData(int(fv))
            if idx >= 0:
                w.setCurrentIndex(idx)
        elif isinstance(w, QDoubleSpinBox):
            w.setValue(fv)
        else:
            w.setValue(int(fv))

    # ── data / CSV ───────────────────────────────────────────────────────
    def _clear_plots(self) -> None:
        self.phasePlot.clear_data()
        self.ampPlot.clear_data()
        self.tempPlot.clear_data()
        self._history.clear()
        self._temp_history.clear()
        self._seq0 = None

    def _save_history(self) -> None:
        if not self._history and not self._temp_history:
            self._append_log("No data to save yet.")
            return
        default = datetime.now().strftime("phase_%Y%m%d_%H%M%S.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Save all data", default, "CSV (*.csv)")
        if path:
            self._write_csv(path)

    def _write_csv(self, path: str) -> bool:
        """F（位相/振幅/周波数）＋温度T＋パラメータ・スナップショットを CSV 保存。"""
        # F と T ストリームを共通時間軸でスパース結合し、時刻順にソート。
        rows = [(t, f"{deg:.3f}", f"{amp:.6f}", f"{freq:.1f}", "", "", "")
                for t, deg, amp, freq in self._history]
        rows += [(t, "", "", "", f"{t1:.3f}", f"{t2:.3f}", f"{t3:.3f}")
                 for t, t1, t2, t3 in self._temp_history]
        rows.sort(key=lambda r: r[0])
        try:
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow([f"# saved {datetime.now().isoformat(timespec='seconds')}"])
                for addr in sorted(self._params):
                    name, val = self._params[addr]
                    w.writerow([f"# param {name}={val}"])
                w.writerow(["time_s", "phase_deg", "amp_v", "freq_hz",
                            "temp_t1_c", "temp_t2_c", "temp_t3_c"])
                for r in rows:
                    w.writerow([f"{r[0]:.4f}", *r[1:]])
            self._append_log(f"Saved {len(rows)} rows to {path}")
            return True
        except OSError as exc:
            self._append_log(f"[error] save failed: {exc}")
            return False

    def _save_point(self, name: str) -> None:
        """スクリプトからの1計測点保存。出力フォルダへ <name>.csv を書き出す。"""
        if not self._history and not self._temp_history:
            self._append_log(f"[skip] '{name}': データがありません")
            return
        base = name if name.lower().endswith(".csv") else f"{name}.csv"
        out_dir = self._out_dir or os.getcwd()
        self._write_csv(os.path.join(out_dir, base))

    # ── 自動計測スクリプト ────────────────────────────────────────────────
    def _load_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load measurement script", "", "Script (*.txt *.scr);;All files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._script_text = f.read()
        except OSError as exc:
            self._append_log(f"[error] script load failed: {exc}")
            return
        self._script_path = path
        # 出力フォルダ既定 = スクリプトと同階層
        self._out_dir = os.path.dirname(os.path.abspath(path))
        try:
            steps = expand_script(self._script_text)
        except ValueError as exc:
            self._append_log(f"[error] script parse: {exc}")
            self._script_text = None
            return
        self.scriptLabel.setText(f"loaded: {os.path.basename(path)} ({len(steps)} steps)")
        self._append_log(f"Script loaded: {path} — {len(steps)} steps")
        self.runScriptButton.setEnabled(self._worker is not None)

    def _run_script(self) -> None:
        if self._worker is None:
            self._append_log("Not connected.")
            return
        if not self._script_text:
            self._append_log("No script loaded.")
            return
        try:
            steps = expand_script(self._script_text)
        except ValueError as exc:
            self._append_log(f"[error] script parse: {exc}")
            return
        if not steps:
            self._append_log("Script is empty.")
            return
        # 出力フォルダを確認（既定＝スクリプトと同階層）
        out_dir = QFileDialog.getExistingDirectory(
            self, "Output folder for saved CSVs", self._out_dir or os.getcwd())
        if not out_dir:
            return
        self._out_dir = out_dir
        self._set_script_running(True)
        self._append_log(f"=== script start: {len(steps)} steps → {out_dir} ===")
        self._runner.start(steps)

    def _on_script_progress(self, text: str) -> None:
        self.scriptLabel.setText(text)

    def _on_script_finished(self) -> None:
        self._append_log("=== script finished ===")
        self._set_script_running(False)

    def _on_script_failed(self, msg: str) -> None:
        self._append_log(f"=== script aborted: {msg} ===")
        self._send("STOP")   # 念のため取得停止
        self._set_script_running(False)

    def _set_script_running(self, on: bool) -> None:
        # 実行中は手動操作を無効化し、Stop script のみ有効
        self.stopScriptButton.setEnabled(on)
        self.runScriptButton.setEnabled(not on and self._script_text is not None
                                        and self._worker is not None)
        self.loadScriptButton.setEnabled(not on)
        for w in (self.runButton, self.stopButton, self.verButton,
                  self.connectButton, self.settingsButton,
                  self.sendButton, self.cmdEdit):
            w.setEnabled(not on if self._worker is not None else w.isEnabled())
        if on:   # 実行中は接続系も触らせない
            self.connectButton.setEnabled(False)

    def _toggle_csv(self) -> None:
        if self._csv_writer is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "phase_log.csv", "CSV (*.csv)")
            if not path:
                return
            self._csv_file = open(path, "w", newline="")
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(["time_s", "phase_deg", "amp_v", "freq_hz",
                                       "temp_t1_c", "temp_t2_c", "temp_t3_c"])
            self.csvButton.setText("Stop CSV log")
            self._append_log(f"Logging to {path}")
        else:
            self._csv_writer = None
            if self._csv_file:
                self._csv_file.close()
                self._csv_file = None
            self.csvButton.setText("Start CSV log…")
            self._append_log("CSV log stopped")

    def closeEvent(self, event) -> None:
        self._runner.stop()
        if self._worker is not None:
            self._worker.stop()
        if self._csv_file:
            self._csv_file.close()
        self._settings.close()   # サブウィンドウも閉じる
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
