"""
config.py
CP-700M の軸設定と単位換算。

CP-700M の PC ダイレクト通信は pulse / pps で扱うため、GUI 表示（mm / mm/s）との換算を
軸ごとに行う。1パルスあたりの移動量はマニュアル §6.1.A より:

    mm_per_pulse = ネジリード[mm] / (500[pulse/回転] × ドライバ分割数)

本設定は「設定ダイアログ」で編集して JSON 保存する。任意で CP-700M 本体パラメータへ
（F:M コマンドで）書き込むこともできる（controller.write_axis_params）。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ── 軸定義（CP-700M は 1/2/3） ────────────────────────────────────────────────

AXES = ("1", "2", "3")

_PULSES_PER_REV = 500   # 5相ステッピングの基準（マニュアル §6.1.A）

# ドライバ分割数の 16 通り（マニュアル §4.4 STAGE*_DIVIDE）。2.5 があるため float。
DIVIDE_OPTIONS = (1, 2, 2.5, 4, 5, 8, 10, 20, 25, 40, 50, 80, 100, 125, 200, 250)


@dataclass
class AxisConfig:
    """1軸分の設定。真の入力値はネジリードと分割数。"""
    lead_mm: float          = 2.0     # ボールねじリード（初期値 2mm）
    divide: float           = 20.0    # ドライバ分割数（初期値 20 分割）
    start_speed_mm_s: float = 2.0     # 自起動速度（D: の初速 S）
    jog_speed_mm_s: float   = 2.0     # 既定ジョグ速度
    move_speed_mm_s: float  = 5.0     # 既定の相対/絶対移動速度
    max_speed_mm_s: float   = 20.0    # 最大速度（初期値 20mm/s）
    accel_ms: int           = 100     # 加減速時間
    soft_limit_cw_mm: float  = 0.0    # ＋方向の上限 [mm]（0 = 無効）
    soft_limit_ccw_mm: float = 0.0    # −方向の下限の絶対値 [mm]（0 = 無効）
    invert: bool            = False   # GUI 論理の ＋/− を反転（ジョグ・相対移動）

    @property
    def mm_per_pulse(self) -> float:
        """[mm/pulse] = lead_mm / (500 × divide)"""
        denom = _PULSES_PER_REV * self.divide
        return self.lead_mm / denom if denom else 0.0

    # ── 換算ヘルパー ────────────────────────────────────────────────────────────

    def mm_to_pulses(self, mm: float) -> int:
        mpp = self.mm_per_pulse
        return round(mm / mpp) if mpp else 0

    def pulses_to_mm(self, pulses: int) -> float:
        return pulses * self.mm_per_pulse

    def mmps_to_pps(self, mm_s: float) -> int:
        mpp = self.mm_per_pulse
        return max(1, round(mm_s / mpp)) if mpp else 1

    def within_soft_limit(self, target_mm: float) -> bool:
        """絶対座標 target_mm[mm] がソフトリミット範囲内か（0 のリミットは無効）。"""
        if self.soft_limit_cw_mm > 0.0 and target_mm > self.soft_limit_cw_mm:
            return False
        if self.soft_limit_ccw_mm > 0.0 and target_mm < -self.soft_limit_ccw_mm:
            return False
        return True


@dataclass
class Cp700Config:
    """3軸設定の集合体と JSON 永続化。"""
    axes: dict[str, AxisConfig] = field(
        default_factory=lambda: {ax: AxisConfig() for ax in AXES}
    )

    def save(self, path: Path) -> None:
        data = {ax: asdict(cfg) for ax, cfg in self.axes.items()}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Cp700Config":
        data = json.loads(path.read_text(encoding="utf-8"))
        # 旧 JSON（新フィールドなし）でも AxisConfig のデフォルトで補完される。
        # 未知キーは無視して既知フィールドだけ取り込む。
        known = set(AxisConfig().__dict__.keys())
        axes = {ax: AxisConfig(**{k: v for k, v in cfg.items() if k in known})
                for ax, cfg in data.items()}
        for ax in AXES:
            axes.setdefault(ax, AxisConfig())
        return cls(axes=axes)

    @classmethod
    def load_or_default(cls, path: Path) -> "Cp700Config":
        try:
            return cls.load(path)
        except Exception:
            return cls()
