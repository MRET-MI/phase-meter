"""センサ特性グラフ（温度 vs 抵抗・電圧・ADC値）を matplotlib の Figure として生成する。

GUI の「特性グラフ」タブに埋め込む。計算は sim.sensor.Sensor を再利用する。
"""
import numpy as np
from matplotlib.figure import Figure

from config import SimConfig
from sim.sensor import Sensor
from blockdiagram import _set_japanese_font

_R_COLOR = "#c0392b"
_V_COLOR = "#2e86c1"
_ADC_COLOR = "#27ae60"
_TARGET = "#8e44ad"


def build_figure(cfg: SimConfig, t_min: float = 0.0, t_max: float = 50.0,
                 n: int = 251) -> Figure:
    """cfg のサーミスタ設定に基づき、温度に対する 抵抗/電圧/ADC の3段グラフを生成する。"""
    _set_japanese_font()
    sensor = Sensor(cfg.thermistor, cfg.adc)

    temps = np.linspace(t_min, t_max, n)
    res = np.array([sensor.resistance(t) for t in temps])
    volt = np.array([sensor.voltage(t) for t in temps])
    adc = np.array([sensor.adc_code(t) for t in temps])

    # 目標温度における各値（動作点の注記用）
    tc = cfg.target_c
    r_at = sensor.resistance(tc)
    v_at = sensor.voltage(tc)
    a_at = sensor.adc_code(tc)

    fig = Figure(figsize=(8.5, 8.0))
    ax_r, ax_v, ax_a = fig.subplots(3, 1, sharex=True)

    # 抵抗（上）
    ax_r.plot(temps, res, color=_R_COLOR, lw=2)
    ax_r.set_ylabel("サーミスタ抵抗 [Ω]")
    ax_r.set_title(f"サーミスタ B定数={cfg.thermistor.b_const:g}, "
                   f"R25={cfg.thermistor.r25:g}Ω"
                   f"分圧1={cfg.thermistor.r_fixed1:g}Ω, 分圧2={cfg.thermistor.r_fixed2:g}Ω, "
                   f"Vref={cfg.thermistor.vref:g}V")

    # 電圧（中）
    ax_v.plot(temps, volt, color=_V_COLOR, lw=2)
    ax_v.set_ylabel("分圧電圧 [V]")

    # ADC値（下）
    ax_a.plot(temps, adc, color=_ADC_COLOR, lw=2)
    ax_a.set_ylabel("ADC値 [code]")
    ax_a.set_xlabel("温度 [℃]")

    # 目標温度の縦線＋動作点マーカーと注記
    for ax, val, txt in ((ax_r, r_at, f"{r_at:,.0f} Ω"),
                         (ax_v, v_at, f"{v_at:.3f} V"),
                         (ax_a, a_at, f"{a_at} code")):
        ax.axvline(tc, color=_TARGET, lw=1, ls="--")
        ax.plot([tc], [val], "o", color=_TARGET, ms=6)
        ax.annotate(f"{tc:g}℃\n{txt}", xy=(tc, val),
                    xytext=(8, 8), textcoords="offset points",
                    fontsize=8, color=_TARGET,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=_TARGET, alpha=0.85))
        ax.grid(True, alpha=0.3)

    fig.suptitle("センサ特性：温度 vs 抵抗・電圧・ADC値", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig
