"""
controller.py
CP-700M への操作をまとめるコントローラ。transport をラップし、commands で組み立てた
コマンドを送信する。駆動/設定系は expect_response=False、確認系は True で送る。
"""
from __future__ import annotations

from dataclasses import dataclass

from comm.transport import Cp700Transport
from . import commands as cmd


@dataclass
class StageStatus:
    """Q: の応答（第1,2,3軸座標,ACK1,ACK2,ACK3）を解釈した結果。"""
    positions: list[int]   # 各軸座標 [pulse]
    accept: str            # ACK1: K=正常受付 / X=コマンド・パラメータエラー
    limit_bits: int        # ACK2: リミットセンサ状態（0..7 のビットコード）
    state: str             # ACK3: B=一部受付 / R=全コマンド受付可 / I=インターロック中
    raw: str

    @property
    def interlocked(self) -> bool:
        return self.state.upper() == "I"

    def limit_on(self, axis_idx: int) -> bool:
        """axis_idx(0-2) のリミットセンサが動作中か（ACK2 のビット）。"""
        return bool(self.limit_bits & (1 << axis_idx))


def parse_status(resp: str) -> StageStatus:
    """Q: の応答文字列を StageStatus に変換する。

    例: "+     100,+     200,+       0,K,7,R"
    """
    parts = [p.strip() for p in resp.split(",")]
    positions: list[int] = []
    for p in parts[:3]:
        token = p.replace(" ", "")
        try:
            positions.append(int(token))
        except ValueError:
            positions.append(0)
    while len(positions) < 3:
        positions.append(0)

    accept = parts[3] if len(parts) > 3 else ""
    try:
        limit_bits = int(parts[4]) if len(parts) > 4 else 0
    except ValueError:
        limit_bits = 0
    state = parts[5] if len(parts) > 5 else ""
    return StageStatus(positions, accept, limit_bits, state, resp)


def _fmt_num(v) -> str:
    """数値を CP-700M 向けの文字列に（整数値は小数点なしで送る）。文字列はそのまま。"""
    if isinstance(v, str):
        return v
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


@dataclass
class Cp700Controller:
    transport: Cp700Transport

    # ── 接続 ──────────────────────────────────────────────────────────────────

    def connect(self) -> None:
        self.transport.open()

    def disconnect(self) -> None:
        self.transport.close()

    def is_connected(self) -> bool:
        return self.transport.is_open()

    # ── 送信ヘルパー ──────────────────────────────────────────────────────────

    def _send(self, command: str, *, expect_response: bool) -> str:
        return self.transport.send_command(command, expect_response=expect_response)

    def send_raw(self, command: str, *, expect_response: bool = True) -> str:
        """直接コマンド入力欄からの任意コマンド送信。"""
        return self._send(command, expect_response=expect_response)

    # ── 確認系（応答あり） ────────────────────────────────────────────────────

    def version(self) -> str:
        return self._send(cmd.version(), expect_response=True)

    def query_status(self) -> StageStatus:
        resp = self._send(cmd.status(), expect_response=True)
        return parse_status(resp)

    def status_fast(self) -> str:
        return self._send(cmd.status_fast(), expect_response=True)

    def query_excitation(self) -> str:
        return self._send(cmd.excitation_query(), expect_response=True)

    # ── 速度設定 ──────────────────────────────────────────────────────────────

    def set_speed(self, axis: str, start_pps: int, max_pps: int, accel_ms: int) -> None:
        # 初速 > 最大 とならないようにクランプ
        start = max(1, min(int(start_pps), int(max_pps)))
        self._send(cmd.speed_set(axis, start, max_pps, accel_ms), expect_response=False)

    # ── 移動（D 速度設定 → M/A セット → G 駆動） ────────────────────────────────

    def move_relative_and_go(self, axis: str, pulses: int, *,
                             start_pps: int, max_pps: int, accel_ms: int) -> None:
        self.set_speed(axis, start_pps, max_pps, accel_ms)
        self._send(cmd.move_relative(axis, pulses), expect_response=False)
        self._send(cmd.drive(), expect_response=False)

    def move_absolute_and_go(self, axis: str, pulses: int, *,
                             start_pps: int, max_pps: int, accel_ms: int) -> None:
        self.set_speed(axis, start_pps, max_pps, accel_ms)
        self._send(cmd.move_absolute(axis, pulses), expect_response=False)
        self._send(cmd.drive(), expect_response=False)

    def move_absolute_multi(self, moves) -> None:
        """複数軸を同時協調で絶対移動する。
        moves: [(axis, pulses, start_pps, max_pps, accel_ms), ...]
        各軸に速度と A: をセットしてから、一括 G: で同時にスタートする。
        """
        for axis, pulses, start_pps, max_pps, accel_ms in moves:
            self.set_speed(axis, start_pps, max_pps, accel_ms)
            self._send(cmd.move_absolute(axis, pulses), expect_response=False)
        self._send(cmd.drive(), expect_response=False)

    def move_relative_multi(self, moves) -> None:
        """複数軸を同時協調で相対移動する。
        moves: [(axis, pulses, start_pps, max_pps, accel_ms), ...]
        各軸に速度と M: をセットしてから、一括 G: で同時にスタートする。
        """
        for axis, pulses, start_pps, max_pps, accel_ms in moves:
            self.set_speed(axis, start_pps, max_pps, accel_ms)
            self._send(cmd.move_relative(axis, pulses), expect_response=False)
        self._send(cmd.drive(), expect_response=False)

    # ── ジョグ（自起動速度=D の初速で連続運転） ──────────────────────────────────

    def jog_start(self, axis: str, positive: bool, *, pps: int, accel_ms: int = 100) -> None:
        # ジョグ速度は自起動速度(S)で決まる。S=F=pps とする。
        self._send(cmd.speed_set(axis, pps, pps, accel_ms), expect_response=False)
        self._send(cmd.jog(axis, positive), expect_response=False)
        self._send(cmd.drive(), expect_response=False)

    def jog_stop(self, axis: str) -> None:
        self._send(cmd.stop(axis), expect_response=False)

    # ── 停止 / 原点 / 座標 / 励磁 ───────────────────────────────────────────────

    def stop(self, axis: str) -> None:
        self._send(cmd.stop(axis), expect_response=False)

    def stop_all(self) -> None:
        self._send(cmd.stop_all(), expect_response=False)

    def stop_immediate(self) -> None:
        """全軸即停止（非常停止相当）。"""
        self._send(cmd.stop_immediate(), expect_response=False)

    def home(self, axis: str, positive: bool | None = None) -> None:
        self._send(cmd.home(axis, positive), expect_response=False)

    def counter_clear(self, axis: str) -> None:
        self._send(cmd.counter_clear(axis), expect_response=False)

    def coord_replace(self, axis: str, pulses: int) -> None:
        self._send(cmd.coord_replace(axis, pulses), expect_response=False)

    def set_excitation(self, axis: str, on: bool) -> None:
        self._send(cmd.excitation(axis, on), expect_response=False)

    # ── 本体パラメータ書き込み（F:M<no>D → 値+EOF の2段） ────────────────────────

    def write_param(self, no: int, value) -> None:
        """1つの本体パラメータを書き込む（COMM RES 非依存のため応答は待たない）。"""
        self._send(cmd.param_write(no), expect_response=False)
        self.transport.send_value(_fmt_num(value), expect_response=False)

    def write_axis_params(self, axis: str, cfg) -> None:
        """設定ダイアログの軸設定を CP-700M 本体パラメータへ書き込む。
        （最高速度・自起動速度・加減速時間・リード・分割数・ソフトリミット）
        ソフトリミットは mm→µm（×1000）。方向反転(invert)は GUI 論理のため書き込まない。
        """
        p = cmd.PARAM_NO[str(axis)]
        self.write_param(p["max_speed"],   cfg.max_speed_mm_s)
        self.write_param(p["start_speed"], cfg.start_speed_mm_s)
        self.write_param(p["accel"],       int(cfg.accel_ms))
        self.write_param(p["lead"],        cfg.lead_mm)
        self.write_param(p["divide"],      cfg.divide)
        self.write_param(p["slimit_f"],    int(round(cfg.soft_limit_cw_mm * 1000)))
        self.write_param(p["slimit_r"],    int(round(cfg.soft_limit_ccw_mm * 1000)))

    # ── トリガ出力（T:） ────────────────────────────────────────────────────────

    def trigger_stop(self) -> None:
        self._send(cmd.trg_stop(), expect_response=False)

    def trigger_oneshot(self) -> None:
        self._send(cmd.trg_oneshot(), expect_response=False)

    def trigger_timer(self, ms: int) -> None:
        self._send(cmd.trg_timer(ms), expect_response=False)

    def trigger_pulse(self, axis: str, pulses: int) -> None:
        self._send(cmd.trg_pulse(axis, pulses), expect_response=False)

    def trigger_constspeed(self, axis: str, pulses: int) -> None:
        self._send(cmd.trg_constspeed(axis, pulses), expect_response=False)

    def trigger_position(self, axis: str, pulses: int) -> None:
        self._send(cmd.trg_position(axis, pulses), expect_response=False)

    def write_trigger_params(self, lev: str, width_us: int) -> None:
        """トリガ本体パラメータを書き込む（No.2 TRG LEV=HI/LO, No.3 TRG WIDTH[µs]）。"""
        self.write_param(cmd.PARAM_TRG_LEV, lev)
        self.write_param(cmd.PARAM_TRG_WIDTH, int(width_us))
