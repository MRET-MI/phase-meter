"""自動計測スクリプトの展開と実行（非ブロッキング状態機械）。

スクリプトはテキスト（1行=1ステップ）。空行と `#` 以降はコメント。
既存のデバイスコマンド（`R2S1000000` / `ATTT10` / `RUNN300` / `RS` / `RA` …）に加え、
以下の制御命令を混在できる（キーワードは大文字小文字を区別しない）:

    LABEL <text>          次に自動保存するファイル名の stem
    WAIT  <sec>           指定秒スリープ（非ブロッキング）
    CLEAR                 グラフ/履歴クリア
    SAVE  [name]          現在の収集データを即保存（省略時は自動名）
    RUNN  <n> / RUNN<n>   n点取得→DONE待ち→その点を自動保存
    SWEEP <var> <start> <stop> <step>
        ... 本体（${var} を置換） ...
    ENDSWEEP              SWEEP..ENDSWEEP は実行前にフラット展開（ネスト可）

`expand_script()` は純関数（テスト可能）。`ScriptRunner` は Qt の QTimer と
シグナルで逐次実行し、`time.sleep` によるブロッキングは行わない。
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

# タイムアウト（ms）。RUNN は取得時間 n×10ms に余裕を加える。
RESP_TIMEOUT_MS = 3000       # OK/NG/END を待つ上限
DONE_MARGIN_MS = 3000        # DONE 待ちの上乗せ余裕
SAMPLE_PERIOD_MS = 10        # 位相出力周期（TIM6 100Hz）
STAGE_TIMEOUT_MS = 120000    # ステージ移動/完了待ちの上限（2 分）

_CONTROL_KW = {"LABEL", "WAIT", "CLEAR", "SAVE", "SWEEP", "ENDSWEEP",
               "STAGE", "MOVE", "MOVEREL", "HOME", "WAITSTAGE"}


@dataclass
class Step:
    """展開後の1ステップ。"""
    kind: str            # CMD/RUNN/WAIT/CLEAR/SAVE/LABEL/STAGE/MOVE/MOVEREL/HOME/WAITSTAGE
    text: str = ""       # CMD/STAGE: 送信文字列 / LABEL,SAVE: 引数 / 表示用
    n: int = 0           # RUNN: サンプル数
    sec: float = 0.0     # WAIT: 秒
    axis: str = ""       # MOVE/MOVEREL/HOME: 軸トークン 1/2/3
    value: float = 0.0   # MOVE/MOVEREL: 位置/移動量 [mm]

    @property
    def display(self) -> str:
        if self.kind in ("CMD", "STAGE"):
            return self.text if self.kind == "CMD" else f"STAGE {self.text}"
        if self.kind == "RUNN":
            return f"RUNN{self.n}"
        if self.kind == "WAIT":
            return f"WAIT {self.sec:g}s"
        if self.kind == "SAVE":
            return f"SAVE {self.text}" if self.text else "SAVE"
        if self.kind == "LABEL":
            return f"LABEL {self.text}"
        if self.kind in ("MOVE", "MOVEREL"):
            return f"{self.kind} {self.axis} {self.value:g}mm"
        if self.kind == "HOME":
            return f"HOME {self.axis}"
        return self.kind


# ── 展開（純関数） ──────────────────────────────────────────────────────────
def _strip_comment(line: str) -> str:
    i = line.find("#")
    if i >= 0:
        line = line[:i]
    return line.strip()


def _fmt_num(v: float) -> str:
    """整数値は整数として、そうでなければ簡潔表記で文字列化。"""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:g}"


def _frange(start: float, stop: float, step: float) -> list[float]:
    if step == 0:
        raise ValueError("SWEEP の step が 0 です")
    n = int(round((stop - start) / step))
    if n < 0:
        raise ValueError("SWEEP の start/stop/step の向きが不整合です")
    return [start + k * step for k in range(n + 1)]


def _apply_subst(line: str, subst: dict) -> str:
    for k, v in subst.items():
        line = line.replace("${" + k + "}", v)
    return line


def _find_matching_end(lines: list[str], start: int) -> int:
    """lines[start] の SWEEP に対応する ENDSWEEP の位置を返す（ネスト対応）。"""
    depth = 1
    j = start + 1
    while j < len(lines):
        kw = lines[j].split()[0].upper()
        if kw == "SWEEP":
            depth += 1
        elif kw == "ENDSWEEP":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("SWEEP に対応する ENDSWEEP がありません")


def _make_step(line: str) -> Step:
    parts = line.split()
    kw = parts[0].upper()
    if kw.startswith("RUNN"):
        # "RUNN300" もしくは "RUNN 300"
        rest = line[4:].strip()
        if not rest and len(parts) > 1:
            rest = parts[1]
        try:
            n = int(rest)
        except ValueError:
            raise ValueError(f"RUNN のサンプル数が不正です: '{line}'")
        if n <= 0:
            raise ValueError(f"RUNN のサンプル数は1以上: '{line}'")
        return Step("RUNN", n=n)
    if kw == "WAIT":
        if len(parts) < 2:
            raise ValueError(f"WAIT に秒数がありません: '{line}'")
        return Step("WAIT", sec=float(parts[1]))
    if kw == "CLEAR":
        return Step("CLEAR")
    if kw == "SAVE":
        return Step("SAVE", text=(parts[1] if len(parts) > 1 else ""))
    if kw == "LABEL":
        return Step("LABEL", text=line[len(parts[0]):].strip())
    # ── CP-700M ステージ制御 ──
    if kw == "STAGE":
        raw = line[len(parts[0]):].strip()
        if not raw:
            raise ValueError(f"STAGE に生コマンドがありません: '{line}'")
        return Step("STAGE", text=raw)
    if kw == "WAITSTAGE":
        return Step("WAITSTAGE")
    if kw == "HOME":
        if len(parts) < 2:
            raise ValueError(f"HOME に軸がありません: '{line}'")
        return Step("HOME", axis=str(parts[1]))
    if kw in ("MOVE", "MOVEREL"):
        if len(parts) < 3:
            raise ValueError(f"{kw} は '<軸> <mm>' が必要です: '{line}'")
        try:
            mm = float(parts[2])
        except ValueError:
            raise ValueError(f"{kw} の mm 値が不正です: '{line}'")
        return Step(kw, axis=str(parts[1]), value=mm)
    # それ以外は生デバイスコマンド
    return Step("CMD", text=line)


def _expand(lines: list[str], subst: dict) -> list[Step]:
    steps: list[Step] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        kw = raw.split()[0].upper()
        if kw == "SWEEP":
            header = _apply_subst(raw, subst)
            hp = header.split()
            if len(hp) < 5:
                raise ValueError(f"SWEEP の書式は 'SWEEP var start stop step': '{raw}'")
            var = hp[1]
            start, stop, step = float(hp[2]), float(hp[3]), float(hp[4])
            end = _find_matching_end(lines, i)
            body = lines[i + 1:end]
            for v in _frange(start, stop, step):
                steps += _expand(body, {**subst, var: _fmt_num(v)})
            i = end + 1
        elif kw == "ENDSWEEP":
            raise ValueError("ENDSWEEP が SWEEP より先にあります")
        else:
            steps.append(_make_step(_apply_subst(raw, subst)))
            i += 1
    return steps


def expand_script(text: str) -> list[Step]:
    """スクリプト文字列を Step のフラット列へ展開する。"""
    lines = [s for s in (_strip_comment(l) for l in text.splitlines()) if s]
    return _expand(lines, {})


# ── 実行（Qt 状態機械） ─────────────────────────────────────────────────────
class ScriptRunner(QObject):
    send_command = Signal(str)     # デバイス（位相計）へ送信
    request_clear = Signal()       # グラフ/履歴クリア
    request_save = Signal(str)     # ファイル名 stem で保存
    stage_step = Signal(object)    # CP-700M ステージ・ステップ（Step を渡す）
    progress = Signal(str)         # 進捗テキスト
    finished = Signal()            # 正常終了
    failed = Signal(str)           # エラー終了

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps: list[Step] = []
        self._i = 0
        self._running = False
        self._await = None          # 'RESP' | 'DONE' | 'STAGE' | None
        self._label = "point"
        self._save_index = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)
        self._timer_mode = "timeout"   # 'timeout' | 'sleep'

    # ── lifecycle ──
    def start(self, steps: list[Step]) -> None:
        self._steps = steps
        self._i = 0
        self._running = True
        self._await = None
        self._label = "point"
        self._save_index = 0
        self.progress.emit(f"0/{len(steps)}")
        self._run_current()

    def stop(self) -> None:
        if self._running:
            self._running = False
            self._timer.stop()
            self.progress.emit("stopped")

    @property
    def running(self) -> bool:
        return self._running

    # ── step execution ──
    def _run_current(self) -> None:
        if not self._running:
            return
        if self._i >= len(self._steps):
            self._running = False
            self.progress.emit(f"done ({len(self._steps)} steps)")
            self.finished.emit()
            return

        step = self._steps[self._i]
        self.progress.emit(f"{self._i + 1}/{len(self._steps)}: {step.display}")

        if step.kind == "CMD":
            self._await = "RESP"
            self._arm_timeout(RESP_TIMEOUT_MS)
            self.send_command.emit(step.text)
        elif step.kind == "RUNN":
            self.request_clear.emit()          # その点のデータを新規収集
            self._await = "DONE"
            self._arm_timeout(step.n * SAMPLE_PERIOD_MS + DONE_MARGIN_MS)
            self.send_command.emit(f"RUNN{step.n}")
        elif step.kind == "WAIT":
            self._await = None
            self._timer_mode = "sleep"
            self._timer.start(max(0, int(step.sec * 1000)))
        elif step.kind == "CLEAR":
            self.request_clear.emit()
            self._advance()
        elif step.kind == "LABEL":
            self._label = step.text or "point"
            self._advance()
        elif step.kind == "SAVE":
            name = step.text or self._auto_name()
            self.request_save.emit(name)
            self._advance()
        elif step.kind in ("STAGE", "MOVE", "MOVEREL", "HOME", "WAITSTAGE"):
            # main.py がステージを実行し、完了で stage_done()／失敗で fail() を呼ぶ。
            self._await = "STAGE"
            self._arm_timeout(STAGE_TIMEOUT_MS)
            self.stage_step.emit(step)
        else:
            self.fail(f"未知のステップ: {step.kind}")

    def _advance(self) -> None:
        if not self._running:
            return
        self._i += 1
        # 即時ステップの連鎖でも呼び出しスタックを浅く保つ
        QTimer.singleShot(0, self._run_current)

    def _auto_name(self) -> str:
        self._save_index += 1
        return f"{self._save_index:02d}_{self._label}"

    def fail(self, msg: str) -> None:
        self._running = False
        self._timer.stop()
        self.failed.emit(msg)

    # ── timers / responses ──
    def _arm_timeout(self, ms: int) -> None:
        self._timer_mode = "timeout"
        self._timer.start(int(ms))

    def _on_timer(self) -> None:
        if not self._running:
            return
        if self._timer_mode == "sleep":
            self._advance()
        else:
            step = self._steps[self._i] if self._i < len(self._steps) else None
            self.fail(f"タイムアウト（応答なし）: step {self._i + 1} "
                      f"{step.display if step else ''}")

    def stage_done(self) -> None:
        """main.py がステージ・ステップの実行を完了したら呼ぶ（次ステップへ）。"""
        if not self._running or self._await != "STAGE":
            return
        self._timer.stop()
        self._await = None
        self._advance()

    def on_line(self, line: str) -> None:
        """MainWindow の受信行を受け取り、待ち条件を満たしたら次へ進む。"""
        if not self._running:
            return
        if self._await == "DONE":
            if line == "DONE":
                self._timer.stop()
                self.request_save.emit(self._auto_name())   # その点を自動保存
                self._await = None
                self._advance()
            # OK（RUNN の即時応答）や他行は無視して DONE を待つ
        elif self._await == "RESP":
            if line in ("OK", "END"):
                self._timer.stop()
                self._await = None
                self._advance()
            elif line == "NG":
                self.fail(f"デバイスが NG を返しました: step {self._i + 1}")
