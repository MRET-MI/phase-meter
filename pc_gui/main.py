"""phase-meter GUI — connect to the STM32 (USB CDC), stream and plot the
2-channel phase difference, and control the HMC8073 attenuators.

Run:  python main.py
Deps: see requirements.txt
"""

from __future__ import annotations

import csv
import sys
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from plot_widget import PhasePlot
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

        # Current value
        self.value_label = QLabel("—")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-size: 40px; font-weight: 600;")
        root.addWidget(self.value_label)

        # Plot
        self.plot = PhasePlot()
        root.addWidget(self.plot, 1)

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
        self.clear_btn.clicked.connect(self.plot.clear_data)
        csv_col.addWidget(self.csv_btn)
        csv_col.addWidget(self.clear_btn)
        csv_col.addStretch(1)
        bottom.addLayout(csv_col)
        root.addLayout(bottom)

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
            worker.phase_received.connect(self._on_phase)
            worker.line_received.connect(self._append_log)
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

    def _on_phase(self, value: float) -> None:
        self.value_label.setText(f"{value:+.3f}°")
        self.plot.add(value)
        if self._csv_writer is not None:
            self._csv_writer.writerow([f"{time.monotonic() - self._t0:.4f}", f"{value:.3f}"])

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
            self._csv_writer.writerow(["time_s", "phase_deg"])
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
