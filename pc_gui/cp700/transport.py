"""
transport.py
COMS CP-700M との通信レイヤ。

CP-700M は USB 仮想COMポート（"CP-700 Communications Port (COM*)"）として現れる機器で、
コマンドは ASCII、行終端は CR+LF。パラメータ 1「COMM RES」が OFF（初期値）の場合、
駆動/設定系コマンドには応答が返らないため、query 系のみ応答を読む設計とする
（送信時に expect_response で切り替える）。
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


class TransportError(RuntimeError):
    pass


class Cp700Transport(ABC):
    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def send_command(self, command: str, *, expect_response: bool = True) -> str:
        """コマンドを送信する。

        expect_response=True  : 応答を1行読み取って返す（query 系）。
        expect_response=False : 書き込みのみで応答を待たない（駆動/設定系）。
                                COMM RES=OFF の無応答でも GUI が固まらない。
        """
        raise NotImplementedError

    @abstractmethod
    def send_value(self, value: str, *, expect_response: bool = False) -> str:
        """F:M<no>D の後続として、値 + EOF(0x1A) を送る（本体パラメータ書き込み）。"""
        raise NotImplementedError


@dataclass
class SerialTransport(Cp700Transport):
    """pyserial 経由の実機通信。行終端は CR+LF。"""
    port: str
    baudrate: int = 115200            # 仮想COMのため実値は無視されるが pyserial に必要
    timeout: float = 1.0
    line_ending: bytes = b"\r\n"

    def __post_init__(self) -> None:
        self._serial = None

    def open(self) -> None:
        try:
            import serial
        except ImportError as exc:
            raise TransportError("pyserial is not installed.") from exc

        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
        except serial.SerialException as exc:
            raise TransportError(str(exc)) from exc

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def is_open(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    def send_command(self, command: str, *, expect_response: bool = True) -> str:
        if not self.is_open():
            raise TransportError("Serial port is not connected.")

        payload = command.encode("ascii") + self.line_ending
        try:
            self._serial.write(payload)
            self._serial.flush()
            if not expect_response:
                return ""
            response = self._serial.readline().decode("ascii", errors="replace").strip()
        except Exception as exc:
            raise TransportError(str(exc)) from exc

        return response or "NO RESPONSE"

    def send_value(self, value: str, *, expect_response: bool = False) -> str:
        if not self.is_open():
            raise TransportError("Serial port is not connected.")

        # F:M<no>D の書き込みデータは EOF(0x1A) で終端する（マニュアル §5.2.20 手順4）。
        payload = value.encode("ascii") + b"\x1a"
        try:
            self._serial.write(payload)
            self._serial.flush()
            if not expect_response:
                return ""
            response = self._serial.readline().decode("ascii", errors="replace").strip()
        except Exception as exc:
            raise TransportError(str(exc)) from exc

        return response or "NO RESPONSE"


@dataclass
class MockTransport(Cp700Transport):
    """実機なしで動作確認するための擬似コントローラ。

    3軸の擬似座標[pulse]を内部に保持し、駆動コマンド（M/A/J/G/H/R/RC）で更新する。
    ジョグ中は Q: 受信（＝ポーリング）のたびに一定量進めるため、表示が動いて見える。
    """
    opened: bool = False
    step_pulses: int = 800    # ジョグ1ポーリングあたりの擬似移動量[pulse]

    _RE_MA = re.compile(r"^([MA]):([123W])([+-])P(\d+)$")
    _RE_J  = re.compile(r"^J:([123W])([+-])$")
    _RE_L  = re.compile(r"^L:([123WE])$")
    _RE_H  = re.compile(r"^H:([123W])")
    _RE_R  = re.compile(r"^R:([123W])$")
    _RE_RC = re.compile(r"^RC:([123W])([+-])P(\d+)$")

    def __post_init__(self) -> None:
        self._pos = [0, 0, 0]
        self._jog = [0, 0, 0]
        self._pending: list[tuple[int, str, int]] = []   # (axis_idx, "M"/"A", signed_value)

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.opened = False

    def is_open(self) -> bool:
        return self.opened

    def send_command(self, command: str, *, expect_response: bool = True) -> str:
        if not self.opened:
            raise TransportError("Mock transport is not connected.")
        return self._handle(command.strip())

    def send_value(self, value: str, *, expect_response: bool = False) -> str:
        if not self.opened:
            raise TransportError("Mock transport is not connected.")
        return "OK"   # 擬似コントローラは書き込みを受理するだけ

    # ── 擬似処理 ────────────────────────────────────────────────────────────────

    def _axes(self, tok: str) -> list[int]:
        return [0, 1, 2] if tok == "W" else [int(tok) - 1]

    def _handle(self, cmd: str) -> str:
        if cmd == "Q:":
            self._advance_jog()
            return self._status()
        if cmd == "V:":
            return "V1.00"
        if cmd == "!:":
            return "R"
        if cmd == "Q3:":
            return "Q3:S1F20000R100,S1F20000R100,S1F20000R100"
        if cmd == "?:":
            return "0"
        if cmd == "I:":
            return "0"
        if cmd == "C:":
            return "1,1,1"

        m = self._RE_RC.match(cmd)
        if m:
            sign = 1 if m.group(2) == "+" else -1
            val = int(m.group(3))
            for i in self._axes(m.group(1)):
                self._pos[i] = sign * val
            return ""

        m = self._RE_MA.match(cmd)
        if m:
            mode = m.group(1)
            sign = 1 if m.group(3) == "+" else -1
            val = int(m.group(4))
            for i in self._axes(m.group(2)):
                self._pending.append((i, mode, sign * val))
            return ""

        m = self._RE_J.match(cmd)
        if m:
            sign = 1 if m.group(2) == "+" else -1
            for i in self._axes(m.group(1)):
                self._jog[i] = sign
            return ""

        if cmd == "G:":
            for i, mode, val in self._pending:
                if mode == "M":
                    self._pos[i] += val
                else:
                    self._pos[i] = val
            self._pending.clear()
            return ""

        m = self._RE_L.match(cmd)
        if m:
            tok = m.group(1)
            if tok in ("W", "E"):
                self._jog = [0, 0, 0]
            else:
                self._jog[int(tok) - 1] = 0
            return ""

        m = self._RE_H.match(cmd)
        if m:
            for i in self._axes(m.group(1)):
                self._pos[i] = 0
                self._jog[i] = 0
            return ""

        m = self._RE_R.match(cmd)
        if m:
            for i in self._axes(m.group(1)):
                self._pos[i] = 0
            return ""

        # C:set / D: / O: / その他 → 応答不要コマンド
        return "OK"

    def _advance_jog(self) -> None:
        for i in range(3):
            if self._jog[i]:
                self._pos[i] += self._jog[i] * self.step_pulses

    def _status(self) -> str:
        coords = ",".join(f"{'+' if p >= 0 else '-'}{abs(p)}" for p in self._pos)
        return f"{coords},K,0,R"
