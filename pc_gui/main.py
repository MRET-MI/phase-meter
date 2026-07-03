"""phase-meter GUI controller.

Layout lives in ui/main_window.ui (edit with pyside6-designer). This file only
wires logic to the widgets (referenced by objectName) and handles serial I/O.

Run:  python main.py     (auto-regenerates ui_main_window.py if the .ui changed)
Deps: see requirements.txt
"""

from __future__ import annotations

import csv
import re
import sys
import time
from datetime import datetime

import regen_ui
regen_ui.ensure_ui()

from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QWidget,
)

from serial_worker import SerialWorker, available_ports

try:
    from ui_main_window import Ui_MainWindow
except ImportError:
    sys.exit("ui_main_window.py missing. Generate it with:\n"
             "    pyside6-uic ui/main_window.ui -o ui_main_window.py")

# Firmware calc/output rate (TIM6 = 100 Hz). Each seq is one 10 ms tick.
SAMPLE_PERIOD_S = 0.01


class MainWindow(QWidget, Ui_MainWindow):
    # Matches an "RA" register-dump line: "<addr>:<name>:<unit>:<val>"
    _RA_RE = re.compile(r"^(\d+):[^:]*:\d+:(-?\d+(?:\.\d+)?)$")

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self._worker: SerialWorker | None = None
        self._csv_writer: csv.writer | None = None
        self._csv_file = None
        self._t0 = time.monotonic()
        self._seq0: int | None = None
        self._history: list[tuple[float, float, float, float]] = []

        self._init_widgets()
        self._wire()
        self._refresh_ports()
        self._set_connected(False)

    # ── setup ────────────────────────────────────────────────────────────
    def _init_widgets(self) -> None:
        for n in (256, 512, 1024, 2048, 4096):
            self.adcNumCombo.addItem(str(n), n)
        self.adcNumCombo.setCurrentText("4096")
        self.peakCombo.addItem("Fixed bin", 0)
        self.peakCombo.addItem("Peak search", 1)
        self.peakCombo.setCurrentIndex(1)
        self.fsSpin.setGroupSeparatorShown(True)
        self.targetSpin.setGroupSeparatorShown(True)

        self.phasePlot.configure(ylabel="Phase difference", yunits="deg",
                                 yrange=(-180, 180), color="#1565c0")
        self.ampPlot.configure(ylabel="Peak amplitude", yunits="V",
                               yrange=None, color="#c62828")

        # firmware register address -> widget (dac_v at 10 is a float register)
        self._reg_widgets = {
            1: self.adcNumCombo,
            2: self.fsSpin,
            3: self.targetSpin,
            4: self.searchWinSpin,
            5: self.bandWSpin,
            6: self.maxOffsetSpin,
            9: self.peakCombo,
            10: self.dacSpin,
        }

    def _wire(self) -> None:
        self.refreshButton.clicked.connect(self._refresh_ports)
        self.connectButton.clicked.connect(self._toggle_connect)
        self.runButton.clicked.connect(lambda: self._send("RUN"))
        self.stopButton.clicked.connect(lambda: self._send("STOP"))
        self.verButton.clicked.connect(lambda: self._send("VER"))
        self.txSetButton.clicked.connect(lambda: self._send(f"ATTT{self.txSpin.value():.1f}"))
        self.rxSetButton.clicked.connect(lambda: self._send(f"ATTR{self.rxSpin.value():.1f}"))
        self.dacSetButton.clicked.connect(lambda: self._send(f"R10S{self.dacSpin.value():.3f}"))
        self.readButton.clicked.connect(self._settings_read)
        self.applyButton.clicked.connect(self._settings_apply)
        self.saveFlashButton.clicked.connect(lambda: self._send("RS"))
        self.sendButton.clicked.connect(self._send_manual)
        self.cmdEdit.returnPressed.connect(self._send_manual)
        self.saveDataButton.clicked.connect(self._save_history)
        self.csvButton.clicked.connect(self._toggle_csv)
        self.clearButton.clicked.connect(self._clear_plots)

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
            worker.line_received.connect(self._on_line)
            worker.error.connect(self._on_error)
            if not worker.open():
                return
            worker.start()
            self._worker = worker
            self._history.clear()
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

    # ── events ───────────────────────────────────────────────────────────
    def _send(self, cmd: str) -> None:
        if self._worker is None:
            self._append_log("Not connected.")
            return
        self._worker.send(cmd)
        self._append_log(f"> {cmd}")

    def _send_manual(self) -> None:
        txt = self.cmdEdit.text().strip()
        if txt:
            self._send(txt)
            self.cmdEdit.clear()

    def _on_sample(self, seq: int, deg: float, amp: float, freq: float) -> None:
        if self._seq0 is None:
            self._seq0 = seq
        t = (seq - self._seq0) * SAMPLE_PERIOD_S   # exact, jitter-free time axis
        self.valueLabel.setText(f"{deg:+.3f}°")
        self.freqLabel.setText(f"peak freq: {freq:,.1f} Hz    amp: {amp * 1000.0:.3f} mV")
        self.phasePlot.add(t, deg)
        self.ampPlot.add(t, amp)
        self._history.append((t, deg, amp, freq))
        if self._csv_writer is not None:
            self._csv_writer.writerow([f"{t:.4f}", f"{deg:.3f}", f"{amp:.6f}", f"{freq:.1f}"])

    def _on_line(self, line: str) -> None:
        self._append_log(line)
        m = self._RA_RE.match(line)
        if m:
            w = self._reg_widgets.get(int(m.group(1)))
            if w is not None:
                self._set_reg_widget(w, m.group(2))

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
        self._history.clear()
        self._seq0 = None

    def _save_history(self) -> None:
        if not self._history:
            self._append_log("No data to save yet.")
            return
        default = datetime.now().strftime("phase_%Y%m%d_%H%M%S.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Save all data", default, "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["time_s", "phase_deg", "amp_v", "freq_hz"])
                for t, deg, amp, freq in self._history:
                    w.writerow([f"{t:.4f}", f"{deg:.3f}", f"{amp:.6f}", f"{freq:.1f}"])
            self._append_log(f"Saved {len(self._history)} rows to {path}")
        except OSError as exc:
            self._append_log(f"[error] save failed: {exc}")

    def _toggle_csv(self) -> None:
        if self._csv_writer is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "phase_log.csv", "CSV (*.csv)")
            if not path:
                return
            self._csv_file = open(path, "w", newline="")
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(["time_s", "phase_deg", "amp_v", "freq_hz"])
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
        if self._worker is not None:
            self._worker.stop()
        if self._csv_file:
            self._csv_file.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
