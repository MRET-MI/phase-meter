"""Serial I/O worker for the phase-meter GUI.

A background QThread reads newline-terminated lines from the virtual COM port
and emits parsed phase values (`F,<deg>`) and raw lines separately. Commands are
written from the GUI thread under a lock.
"""

from __future__ import annotations

import threading

import serial
from serial.tools import list_ports
from PySide6.QtCore import QThread, Signal


def available_ports() -> list[tuple[str, str]]:
    """Return [(device, description), ...] for the connected serial ports."""
    return [(p.device, p.description) for p in list_ports.comports()]


class SerialWorker(QThread):
    # parsed "F,<seq>,<deg>,<amp_v>,<freq_hz>" stream sample
    sample_received = Signal(int, float, float, float)
    line_received = Signal(str)      # any other line (OK / NG / VER / ...)
    error = Signal(str)
    connected = Signal(bool)

    def __init__(self, port: str, baud: int = 115200, parent=None):
        super().__init__(parent)
        self._port = port
        self._baud = baud
        self._ser: serial.Serial | None = None
        self._write_lock = threading.Lock()
        self._running = False

    # ── lifecycle ────────────────────────────────────────────────────────
    def open(self) -> bool:
        try:
            # CDC ignores the baud rate, but pyserial requires a value.
            self._ser = serial.Serial(self._port, self._baud, timeout=0.1)
        except serial.SerialException as exc:
            self.error.emit(str(exc))
            return False
        self.connected.emit(True)
        return True

    def run(self) -> None:
        self._running = True
        buf = bytearray()
        while self._running and self._ser is not None:
            try:
                # Read whatever has arrived immediately (low latency); block on
                # 1 byte only when idle. Reading a fixed 256 would batch ~9 lines
                # (256 B / ~3000 B/s ≈ 85 ms) instead of delivering each 10 ms.
                n = self._ser.in_waiting
                chunk = self._ser.read(n if n > 0 else 1)
            except serial.SerialException as exc:
                self.error.emit(str(exc))
                break
            if not chunk:
                continue
            buf.extend(chunk)
            while b"\n" in buf:
                raw, _, rest = buf.partition(b"\n")
                buf = bytearray(rest)
                self._handle_line(raw.decode("ascii", "replace").strip())
        self._running = False

    def stop(self) -> None:
        self._running = False
        self.wait(1000)
        if self._ser is not None:
            try:
                self._ser.close()
            except serial.SerialException:
                pass
            self._ser = None
        self.connected.emit(False)

    # ── parsing / sending ────────────────────────────────────────────────
    def _handle_line(self, line: str) -> None:
        if not line:
            return
        if line.startswith("F,"):
            parts = line.split(",")
            try:
                seq = int(parts[1])
                deg = float(parts[2])
                amp = float(parts[3]) if len(parts) > 3 else float("nan")
                freq = float(parts[4]) if len(parts) > 4 else float("nan")
                self.sample_received.emit(seq, deg, amp, freq)
                return
            except (ValueError, IndexError):
                pass
        self.line_received.emit(line)

    def send(self, command: str) -> None:
        """Send a command (a trailing '\\n' is added if missing)."""
        if self._ser is None:
            return
        if not command.endswith("\n"):
            command += "\n"
        with self._write_lock:
            try:
                self._ser.write(command.encode("ascii"))
            except serial.SerialException as exc:
                self.error.emit(str(exc))
