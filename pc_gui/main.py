"""phase-meter GUI — connect to the STM32 (USB CDC), stream and plot the
2-channel phase difference, and control the HMC8073 attenuators.

Run:  python main.py
Deps: see requirements.txt
"""

from __future__ import annotations

import csv
import re
import sys
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from plot_widget import RollingPlot
from serial_worker import SerialWorker, available_ports


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phase Meter — 2ch phase difference")
        self.resize(900, 600)

        self._worker: SerialWorker | None = None
        self._csv_writer: csv.writer | None = None
        self._csv_file = None
        self._t0 = time.monotonic()

        self._build_ui()
        self._refresh_ports()
        self._set_connected(False)

    # ── UI ───────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Connection row
        conn = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(280)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connect)
        conn.addWidget(QLabel("Port:"))
        conn.addWidget(self.port_combo, 1)
        conn.addWidget(self.refresh_btn)
        conn.addWidget(self.connect_btn)
        root.addLayout(conn)

        # Control row
        ctrl = QHBoxLayout()
        self.run_btn = QPushButton("RUN")
        self.run_btn.clicked.connect(lambda: self._send("RUN"))
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.clicked.connect(lambda: self._send("STOP"))
        self.ver_btn = QPushButton("VER")
        self.ver_btn.clicked.connect(lambda: self._send("VER"))
        ctrl.addWidget(self.run_btn)
        ctrl.addWidget(self.stop_btn)
        ctrl.addWidget(self.ver_btn)
        ctrl.addStretch(1)
        ctrl.addWidget(self._attenuator_box())
        root.addLayout(ctrl)

        # Measurement settings panel
        root.addWidget(self._settings_box())

        # Manual command entry (e.g. DBG, R1R, VER)
        cmd_row = QHBoxLayout()
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("send command (e.g. DBG, R1R) — Enter to send")
        self.cmd_edit.returnPressed.connect(self._send_manual)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._send_manual)
        cmd_row.addWidget(QLabel("Cmd:"))
        cmd_row.addWidget(self.cmd_edit, 1)
        cmd_row.addWidget(send_btn)
        root.addLayout(cmd_row)

        # Current value (phase) + peak frequency / amplitude readout
        self.value_label = QLabel("—")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-size: 40px; font-weight: 600;")
        root.addWidget(self.value_label)

        self.freq_label = QLabel("peak freq: —    amp: —")
        self.freq_label.setAlignment(Qt.AlignCenter)
        self.freq_label.setStyleSheet("font-size: 16px; color: #555;")
        root.addWidget(self.freq_label)

        # Stacked plots: phase difference (top) and peak amplitude (bottom)
        self.plot = RollingPlot(ylabel="Phase difference", yunits="deg",
                                yrange=(-180, 180), color="#1565c0")
        self.amp_plot = RollingPlot(ylabel="Peak amplitude", yunits="V",
                                    yrange=None, color="#c62828")
        root.addWidget(self.plot, 1)
        root.addWidget(self.amp_plot, 1)

        # Log + CSV
        bottom = QHBoxLayout()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setFixedHeight(120)
        bottom.addWidget(self.log, 1)

        csv_col = QVBoxLayout()
        self.csv_btn = QPushButton("Start CSV log…")
        self.csv_btn.clicked.connect(self._toggle_csv)
        self.clear_btn = QPushButton("Clear plot")
        self.clear_btn.clicked.connect(self._clear_plots)
        csv_col.addWidget(self.csv_btn)
        csv_col.addWidget(self.clear_btn)
        csv_col.addStretch(1)
        bottom.addLayout(csv_col)
        root.addLayout(bottom)

    def _settings_box(self) -> QGroupBox:
        """Measurement parameters, mapped to firmware registers R<addr>."""
        box = QGroupBox("Settings (phase calc)")
        g = QGridLayout(box)

        self.adc_num_combo = QComboBox()
        for n in (256, 512, 1024, 2048, 4096):
            self.adc_num_combo.addItem(str(n), n)
        self.adc_num_combo.setCurrentText("4096")

        self.fs_spin = QSpinBox()
        self.fs_spin.setRange(4000, 2500000)
        self.fs_spin.setSingleStep(1000)
        self.fs_spin.setSuffix(" Hz")
        self.fs_spin.setGroupSeparatorShown(True)
        self.fs_spin.setValue(1000000)

        self.target_spin = QSpinBox()
        self.target_spin.setRange(1, 1250000)
        self.target_spin.setSuffix(" Hz")
        self.target_spin.setGroupSeparatorShown(True)
        self.target_spin.setValue(100000)

        self.peak_combo = QComboBox()
        self.peak_combo.addItem("Fixed bin", 0)
        self.peak_combo.addItem("Peak search", 1)
        self.peak_combo.setCurrentIndex(1)

        self.searchwin_spin = QSpinBox()
        self.searchwin_spin.setRange(0, 500)
        self.searchwin_spin.setValue(20)

        self.bandw_spin = QSpinBox()
        self.bandw_spin.setRange(0, 50)
        self.bandw_spin.setValue(2)

        self.maxoffset_spin = QSpinBox()
        self.maxoffset_spin.setRange(1, 500)
        self.maxoffset_spin.setValue(10)

        fields = [
            ("adc_num", self.adc_num_combo),
            ("fs", self.fs_spin),
            ("target", self.target_spin),
            ("peak", self.peak_combo),
            ("search_win", self.searchwin_spin),
            ("band_w", self.bandw_spin),
            ("maxoffset", self.maxoffset_spin),
        ]
        for i, (lbl, w) in enumerate(fields):
            r, c = divmod(i, 4)
            g.addWidget(QLabel(lbl), r, c * 2)
            g.addWidget(w, r, c * 2 + 1)

        read_btn = QPushButton("Read")
        read_btn.clicked.connect(self._settings_read)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._settings_apply)
        save_btn = QPushButton("Save→Flash")
        save_btn.clicked.connect(lambda: self._send("RS"))
        g.addWidget(read_btn, 0, 8)
        g.addWidget(apply_btn, 1, 8)
        g.addWidget(save_btn, 1, 9)

        # firmware register address -> widget
        self._reg_widgets = {
            1: self.adc_num_combo,
            2: self.fs_spin,
            3: self.target_spin,
            4: self.searchwin_spin,
            5: self.bandw_spin,
            6: self.maxoffset_spin,
            9: self.peak_combo,
        }
        return box

    def _settings_read(self) -> None:
        """Ask the device to dump all registers; _on_line updates the fields."""
        self._send("RA")

    def _settings_apply(self) -> None:
        for addr, w in self._reg_widgets.items():
            val = w.currentData() if isinstance(w, QComboBox) else w.value()
            self._send(f"R{addr}S{int(val)}")

    @staticmethod
    def _set_reg_widget(w, val_str: str) -> None:
        try:
            iv = int(float(val_str))
        except ValueError:
            return
        if isinstance(w, QComboBox):
            idx = w.findData(iv)
            if idx >= 0:
                w.setCurrentIndex(idx)
        else:
            w.setValue(iv)

    def _attenuator_box(self) -> QGroupBox:
        box = QGroupBox("Attenuator [dB]")
        lay = QHBoxLayout(box)
        self.tx_spin = QDoubleSpinBox()
        self.rx_spin = QDoubleSpinBox()
        for sp in (self.tx_spin, self.rx_spin):
            sp.setRange(0.0, 31.5)
            sp.setSingleStep(0.5)
            sp.setDecimals(1)
        tx_btn = QPushButton("Set TX")
        rx_btn = QPushButton("Set RX")
        tx_btn.clicked.connect(lambda: self._send(f"ATTT{self.tx_spin.value():.1f}"))
        rx_btn.clicked.connect(lambda: self._send(f"ATTR{self.rx_spin.value():.1f}"))
        lay.addWidget(QLabel("TX"))
        lay.addWidget(self.tx_spin)
        lay.addWidget(tx_btn)
        lay.addSpacing(8)
        lay.addWidget(QLabel("RX"))
        lay.addWidget(self.rx_spin)
        lay.addWidget(rx_btn)
        return box

    # ── connection ───────────────────────────────────────────────────────
    def _refresh_ports(self) -> None:
        self.port_combo.clear()
        for device, desc in available_ports():
            self.port_combo.addItem(f"{device} — {desc}", device)
        if self.port_combo.count() == 0:
            self.port_combo.addItem("(no ports found)", None)

    def _toggle_connect(self) -> None:
        if self._worker is None:
            device = self.port_combo.currentData()
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
            self._set_connected(True)
            self._append_log(f"Connected to {device}")
        else:
            self._send("STOP")
            self._worker.stop()
            self._worker = None
            self._set_connected(False)
            self._append_log("Disconnected")

    def _set_connected(self, on: bool) -> None:
        self.connect_btn.setText("Disconnect" if on else "Connect")
        self.port_combo.setEnabled(not on)
        self.refresh_btn.setEnabled(not on)
        for w in (self.run_btn, self.stop_btn, self.ver_btn):
            w.setEnabled(on)

    # ── events ───────────────────────────────────────────────────────────
    def _send(self, cmd: str) -> None:
        if self._worker is None:
            self._append_log("Not connected.")
            return
        self._worker.send(cmd)
        self._append_log(f"> {cmd}")

    def _clear_plots(self) -> None:
        self.plot.clear_data()
        self.amp_plot.clear_data()

    def _send_manual(self) -> None:
        txt = self.cmd_edit.text().strip()
        if txt:
            self._send(txt)
            self.cmd_edit.clear()

    def _on_sample(self, deg: float, amp: float, freq: float) -> None:
        self.value_label.setText(f"{deg:+.3f}°")
        self.freq_label.setText(f"peak freq: {freq:,.1f} Hz    amp: {amp * 1000.0:.3f} mV")
        self.plot.add(deg)
        self.amp_plot.add(amp)
        if self._csv_writer is not None:
            self._csv_writer.writerow(
                [f"{time.monotonic() - self._t0:.4f}", f"{deg:.3f}", f"{amp:.5f}", f"{freq:.1f}"]
            )

    # Matches an "RA" register-dump line: "<addr>:<name>:<unit>:<val>"
    _RA_RE = re.compile(r"^(\d+):[^:]*:\d+:(-?\d+(?:\.\d+)?)$")

    def _on_line(self, line: str) -> None:
        self._append_log(line)
        m = self._RA_RE.match(line)
        if m:
            addr = int(m.group(1))
            w = self._reg_widgets.get(addr)
            if w is not None:
                self._set_reg_widget(w, m.group(2))

    def _on_error(self, msg: str) -> None:
        self._append_log(f"[error] {msg}")

    def _append_log(self, text: str) -> None:
        self.log.appendPlainText(text)

    # ── CSV ──────────────────────────────────────────────────────────────
    def _toggle_csv(self) -> None:
        if self._csv_writer is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "phase_log.csv", "CSV (*.csv)")
            if not path:
                return
            self._csv_file = open(path, "w", newline="")
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(["time_s", "phase_deg", "amp_v", "freq_hz"])
            self._t0 = time.monotonic()
            self.csv_btn.setText("Stop CSV log")
            self._append_log(f"Logging to {path}")
        else:
            self._csv_writer = None
            if self._csv_file:
                self._csv_file.close()
                self._csv_file = None
            self.csv_btn.setText("Start CSV log…")
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
