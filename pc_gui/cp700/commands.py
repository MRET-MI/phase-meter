"""
commands.py
COMS CP-700M の PC ダイレクト通信制御モード（マニュアル §5.2.B.III）コマンドを組み立てる純関数群。

- 軸トークンは "1"/"2"/"3"（全軸 = "W"）。
- 位置・移動量は pulse、速度は pps、加減速は ms。
- 相対/絶対移動は「M/A でセット → G で駆動」の2段。パルスは絶対値、方向は符号(+/-)で指定。
"""
from __future__ import annotations

_VALID_AXES = {"1", "2", "3", "W"}


def axis_token(axis: str | int) -> str:
    """"1"/"2"/"3"/"W" を検証して返す。"""
    tok = str(axis).strip().upper()
    if tok not in _VALID_AXES:
        raise ValueError(f"Unknown axis: {axis!r} (expected 1/2/3/W)")
    return tok


def _sign(value: int) -> str:
    return "+" if value >= 0 else "-"


# ── 確認系（応答あり） ─────────────────────────────────────────────────────────

def version() -> str:
    """V:  ファームウェアバージョン照会"""
    return "V:"


def status() -> str:
    """Q:  座標値＋リミットセンサ＋受付状態（第1,2,3軸座標,ACK1,ACK2,ACK3）"""
    return "Q:"


def status_fast() -> str:
    """!:  コントローラ状態（B/R/I）— Q より高速"""
    return "!:"


def speed_query() -> str:
    """Q3:  速度設定の確認"""
    return "Q3:"


def excitation_query() -> str:
    """C:  励磁状態の確認（例: 1,1,1）"""
    return "C:"


def input_read() -> str:
    """I:  汎用入力ポートの状態読み取り"""
    return "I:"


# ── 設定系（COMM RES=OFF では応答なし） ───────────────────────────────────────

def speed_set(axis: str | int, start_pps: int, max_pps: int, accel_ms: int) -> str:
    """D:<axis>S<init>F<max>R<accel>  駆動速度設定
    S=初速度[pps], F=最大速度[pps], R=加減速時間[ms]。
    """
    return f"D:{axis_token(axis)}S{int(start_pps)}F{int(max_pps)}R{int(accel_ms)}"


def excitation(axis: str | int, on: bool) -> str:
    """C:<axis>1 / C:<axis>0  モータ励磁 ON/OFF"""
    return f"C:{axis_token(axis)}{'1' if on else '0'}"


def output_set(bits: int) -> str:
    """O:<bits>  汎用出力ポート制御（8bit を10進で指定）"""
    return f"O:{int(bits)}"


# ── 駆動系（COMM RES=OFF では応答なし） ───────────────────────────────────────

def jog(axis: str | int, positive: bool) -> str:
    """J:<axis>+ / J:<axis>-  ジョグ（自起動速度で連続定速運転）。G: で開始。"""
    return f"J:{axis_token(axis)}{'+' if positive else '-'}"


def move_relative(axis: str | int, pulses: int) -> str:
    """M:<axis>±P<|pulses|>  相対移動をセット（方向は符号で決定）。G: で駆動。"""
    return f"M:{axis_token(axis)}{_sign(pulses)}P{abs(int(pulses))}"


def move_absolute(axis: str | int, pulses: int) -> str:
    """A:<axis>±P<|pulses|>  絶対移動をセット（方向は符号で決定）。G: で駆動。"""
    return f"A:{axis_token(axis)}{_sign(pulses)}P{abs(int(pulses))}"


def drive() -> str:
    """G:  駆動開始（M/A/J/E/K セット後に実行）"""
    return "G:"


def stop(axis: str | int) -> str:
    """L:<axis>  指定軸を減速停止"""
    return f"L:{axis_token(axis)}"


def stop_all() -> str:
    """L:W  全軸を減速停止"""
    return "L:W"


def stop_immediate() -> str:
    """L:E  全軸を即停止（非常停止相当）"""
    return "L:E"


def home(axis: str | int, positive: bool | None = None) -> str:
    """H:<axis>[+/-]  機械原点復帰。方向省略時はパラメータの既定方向。"""
    base = f"H:{axis_token(axis)}"
    if positive is None:
        return base
    return base + ("+" if positive else "-")


def counter_clear(axis: str | int) -> str:
    """R:<axis>  現在座標値を 0 にする"""
    return f"R:{axis_token(axis)}"


def coord_replace(axis: str | int, pulses: int) -> str:
    """RC:<axis>±P<|pulses|>  現在座標値を指定値に書き換え"""
    return f"RC:{axis_token(axis)}{_sign(pulses)}P{abs(int(pulses))}"


# ── 本体パラメータ（F:M） ─────────────────────────────────────────────────────

# CP-700M 内部パラメータ番号（マニュアル §4.4）。軸 -> {キー: 番号}。
PARAM_NO = {
    "1": {"max_speed": 4,  "start_speed": 5,  "accel": 6,  "lead": 7,  "divide": 12, "slimit_f": 18, "slimit_r": 19},
    "2": {"max_speed": 25, "start_speed": 26, "accel": 27, "lead": 28, "divide": 33, "slimit_f": 39, "slimit_r": 40},
    "3": {"max_speed": 46, "start_speed": 47, "accel": 48, "lead": 49, "divide": 54, "slimit_f": 60, "slimit_r": 61},
}


def param_write(no: int) -> str:
    """F:M<no>D  パラメータ書き込み開始（この後に 値+EOF を送る）"""
    return f"F:M{int(no)}D"


def param_read(no: int) -> str:
    """F:M<no>U  パラメータ読み出し"""
    return f"F:M{int(no)}U"


# トリガ出力の本体パラメータ番号（軸非依存、マニュアル §4.4）。
PARAM_TRG_LEV   = 2   # HI/LO（トリガ非出力時の論理レベル）
PARAM_TRG_WIDTH = 3   # トリガパルス幅 [µs]（10〜100000）


# ── トリガ出力（T:） マニュアル §5.2.15 ─────────────────────────────────────────

def trg_stop() -> str:
    """T:S  トリガ出力を禁止（出力待機状態を解除）"""
    return "T:S"


def trg_oneshot() -> str:
    """T:M  コマンド受付時にトリガを1回出力"""
    return "T:M"


def trg_timer(ms: int) -> str:
    """T:T<ms>  指定時間ごとにトリガ出力（1〜100000 ms）"""
    return f"T:T{int(ms)}"


def trg_pulse(axis: str | int, pulses: int) -> str:
    """T:P<axis>P<pulses>  指定軸の指定パルス移動ごとにトリガ出力"""
    return f"T:P{axis_token(axis)}P{int(pulses)}"


def trg_constspeed(axis: str | int, pulses: int) -> str:
    """T:<axis>TP<pulses>  定速域で指定パルス間隔ごとにトリガ出力"""
    return f"T:{axis_token(axis)}TP{int(pulses)}"


def trg_position(axis: str | int, pulses: int) -> str:
    """T:<axis>±P<|abs|>  移動中、指定絶対座標でトリガ出力（駆動コマンド発行前に設定）"""
    return f"T:{axis_token(axis)}{_sign(pulses)}P{abs(int(pulses))}"
