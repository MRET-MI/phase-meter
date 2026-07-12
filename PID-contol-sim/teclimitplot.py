"""TEC リミット理解用グラフ（V–I 平面）。

ペルチェの TEC 電圧–電流 平面に、負荷線・ADN8834 の Vlim/Ilim・定格×derate の
安全域・実効最大点・現在の指令比率での動作点を重ね描きし、
どのリミットが律速するか／安全域に入っているかを視覚的に把握できるようにする。
"""
import numpy as np
from matplotlib.patches import Rectangle

import tecdriver
from blockdiagram import _set_japanese_font


def draw(fig, cfg) -> None:
    """既存の Figure をクリアして V–I リミット図を描画する（比率変更時に再描画）。"""
    _set_japanese_font()
    fig.clear()
    ax = fig.add_subplot(111)

    tec = cfg.tec
    pl = cfg.peltier
    ev = tecdriver.evaluate(tec, pl)
    lim = tecdriver.compute_limits(tec)
    r = pl.r_elec
    vsafe, isafe = ev["vsafe"], ev["isafe"]
    cool, heat = ev["cool"], ev["heat"]

    # 表示範囲
    vpos = max(lim["vlim_cool"], cool["veff"], vsafe, pl.v_rating) * 1.15
    vneg = -max(lim["vlim_heat"], heat["veff"], vsafe, pl.v_rating) * 1.15
    ipos = max(lim["ilim_cool"], cool["ieff"], isafe, pl.i_rating) * 1.15
    ineg = -max(lim["ilim_heat"], heat["ieff"], isafe, pl.i_rating) * 1.15

    # 定格×derate 安全域
    ax.add_patch(Rectangle(
        (-vsafe, -isafe), 2 * vsafe, 2 * isafe,
        facecolor="#c8e6c9", edgecolor="#2e7d32", alpha=0.5,
        label=f"定格×{tec.derate:g} 安全域"))

    # 負荷線 I = V/R
    vline = np.array([vneg, vpos])
    ax.plot(vline, vline / r, color="#555555", lw=1.5,
            label=f"負荷線 I=V/R (R={r:g}Ω)")

    # ADN8834 Vlim / Ilim（冷却=正, 加熱=負）
    ax.axvline(lim["vlim_cool"], color="#c62828", ls="--", lw=1.2, label="Vlim")
    ax.axvline(-lim["vlim_heat"], color="#c62828", ls="--", lw=1.2)
    ax.axhline(lim["ilim_cool"], color="#1565c0", ls=":", lw=1.4, label="Ilim")
    ax.axhline(-lim["ilim_heat"], color="#1565c0", ls=":", lw=1.4)

    # 実効最大点（負荷線と律速リミットの交点）
    ax.plot([cool["veff"], -heat["veff"]], [cool["ieff"], -heat["ieff"]],
            "o", color="#ef6c00", ms=8, label="実効最大")
    ax.annotate(f"実効最大(冷)\n{cool['veff']:.2f}V / {cool['ieff']:.2f}A\n律速:{cool['binding']}",
                (cool["veff"], cool["ieff"]), textcoords="offset points",
                xytext=(8, -6), fontsize=8, color="#ef6c00")
    ax.annotate(f"実効最大(温)\n{heat['veff']:.2f}V / {heat['ieff']:.2f}A",
                (-heat["veff"], -heat["ieff"]), textcoords="offset points",
                xytext=(-10, 8), ha="right", fontsize=8, color="#ef6c00")

    # 現在の指令比率での動作点
    ax.plot([cool["v_tec"], -heat["v_tec"]], [cool["i_tec"], -heat["i_tec"]],
            "s", color="#6a1b9a", ms=9, label="動作点(現比率)")
    ax.annotate(f"冷 比率{cool['ratio']:.2f}", (cool["v_tec"], cool["i_tec"]),
                textcoords="offset points", xytext=(8, 8), fontsize=8, color="#6a1b9a")

    # 軸
    ax.axhline(0, color="#999999", lw=0.8)
    ax.axvline(0, color="#999999", lw=0.8)
    ax.set_xlim(vneg, vpos)
    ax.set_ylim(ineg, ipos)
    ax.set_xlabel("TEC 電圧 [V]（右=冷却 / 左=加熱）")
    ax.set_ylabel("TEC 電流 [A]")
    ax.set_title("TEC 動作点とリミット（V–I 平面）")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

    fig.tight_layout()
