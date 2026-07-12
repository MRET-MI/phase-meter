"""制御ブロック図（フル詳細）を matplotlib の Figure として生成する。

GUI の「ブロック図」タブに埋め込む。config の代表値を注記に反映する。
日本語ラベルは日本語フォント、伝達関数などの数式は mathtext（$...$）で描画する。
"""
import matplotlib
import matplotlib.font_manager as fm
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

from config import SimConfig
import tecdriver

# 配色
_FC = "#eef3fb"      # ブロック背景
_EC = "#3b6ea5"      # ブロック枠
_SUMFC = "#fff2cc"   # 加算点背景
_ARROW = "#333333"


def _set_japanese_font():
    """Windows で入手可能な日本語フォントを matplotlib に設定する。"""
    candidates = ["Yu Gothic", "Yu Gothic UI", "Meiryo", "MS Gothic", "MS PGothic"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


def _box(ax, cx, cy, w, h, title, details=None):
    """角丸ブロックを描き、位置情報の dict を返す。"""
    patch = FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.5, edgecolor=_EC, facecolor=_FC, zorder=3,
    )
    ax.add_patch(patch)
    if details:
        ax.text(cx, cy + h * 0.30, title, ha="center", va="center",
                fontsize=10, fontweight="bold", zorder=5)
        ax.text(cx, cy - h * 0.14, "\n".join(details), ha="center", va="center",
                fontsize=8, zorder=5)
    else:
        ax.text(cx, cy, title, ha="center", va="center",
                fontsize=10, fontweight="bold", zorder=5)
    return dict(cx=cx, cy=cy, l=cx - w / 2, r=cx + w / 2, t=cy + h / 2, b=cy - h / 2)


def _sumj(ax, cx, cy, r=0.34):
    """加算点（十字入りの円）を描く。"""
    ax.add_patch(Circle((cx, cy), r, facecolor=_SUMFC, edgecolor=_EC,
                        linewidth=1.5, zorder=4))
    ax.plot([cx - r * 0.55, cx + r * 0.55], [cy, cy], color=_EC, lw=1.0, zorder=5)
    ax.plot([cx, cx], [cy - r * 0.55, cy + r * 0.55], color=_EC, lw=1.0, zorder=5)
    return dict(cx=cx, cy=cy, l=cx - r, r=cx + r, t=cy + r, b=cy - r)


def _arrow(ax, x1, y1, x2, y2, label=None, lx=None, ly=None, fontsize=8):
    """矢印を描く。label 指定時は経路近傍に注記する。"""
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
        linewidth=1.4, color=_ARROW, zorder=2,
    ))
    if label:
        if lx is None:
            lx = (x1 + x2) / 2
        if ly is None:
            ly = (y1 + y2) / 2 + 0.28
        ax.text(lx, ly, label, ha="center", va="center", fontsize=fontsize,
                color="#222", zorder=6)


def _line(ax, xs, ys):
    """折れ線（矢印なしの配線）。"""
    ax.plot(xs, ys, color=_ARROW, lw=1.4, zorder=2)


def build_figure(cfg: SimConfig) -> Figure:
    """cfg の値を反映した制御ブロック図の Figure を生成する。"""
    _set_japanese_font()

    fig = Figure(figsize=(14.5, 6.8))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.axis("off")

    y_main = 5.4   # 前向き経路の高さ
    y_fb = 2.2     # フィードバック経路の高さ
    h = 1.55

    th = cfg.thermistor
    pid = cfg.pid
    pl = cfg.peltier
    tm = cfg.thermal
    tec = cfg.tec
    lim = tecdriver.compute_limits(tec)

    # --- 前向き経路のブロック ---
    sp = _box(ax, 1.35, y_main, 1.7, h, "目標値",
              [f"{cfg.target_c:g}℃", "→ 目標ADC"])
    s1 = _sumj(ax, 3.0, y_main)
    pidb = _box(ax, 5.0, y_main, 2.0, h, "PID",
                [f"Kp={pid.kp:g} Ki={pid.ki:g}", f"Kd={pid.kd:g}",
                 "アンチワインドアップ", "クランプ ±32768"])
    dac = _box(ax, 7.1, y_main, 1.8, h, "DAC",
               ["16bit 量子化", "双極性", "中央=無駆動"])
    adn = _box(ax, 9.55, y_main, 2.6, h, "ADN8834 (TECドライバ)",
               [r"$V_{TEC}=5(\frac{VREF}{2}-V_{OUT2})$",
                f"Vlim 冷{lim['vlim_cool']:.1f}/温{lim['vlim_heat']:.1f}V",
                f"Ilim 冷{lim['ilim_cool']:.2f}/温{lim['ilim_heat']:.2f}A",
                "負荷線+VDD で制限"])
    pel = _box(ax, 12.0, y_main, 2.0, h, "ペルチェ",
               [r"$Q=k_{pelt}\,V_{TEC}$",
                f"k={pl.k_pelt:g}W/V, ±{pl.q_max:g}W",
                f"$I=V_{{TEC}}/R$, R={pl.r_elec:g}Ω"])
    s2 = _sumj(ax, 13.85, y_main)
    thm = _box(ax, 15.85, y_main, 2.0, h, "熱系 (プラント)",
               [r"$\frac{1}{C\,s + 1/R_{th}}$",
                f"C={tm.heat_capacity:g} J/K", f"Rth={tm.r_thermal:g} K/W"])

    # --- フィードバック経路のブロック ---
    sen = _box(ax, 13.5, y_fb, 2.6, h, "サーミスタ",
               [r"$R=R_{25}e^{B(1/T-1/T_{25})}$",
                f"NTC, B={th.b_const:g}", "→ 分圧電圧"])
    adc = _box(ax, 7.1, y_fb, 1.8, h, "ADC",
               ["16bit 量子化", "→ 測定ADC"])

    # --- 前向きの矢印 ---
    _arrow(ax, sp["r"], y_main, s1["l"], y_main)
    _arrow(ax, s1["r"], y_main, pidb["l"], y_main, "e (誤差)")
    _arrow(ax, pidb["r"], y_main, dac["l"], y_main, "u")
    _arrow(ax, dac["r"], y_main, adn["l"], y_main, "指令電圧(OUT2)")
    ax.text((dac["r"] + adn["l"]) / 2, y_main - 0.30, "0〜2.5V",
            ha="center", va="center", fontsize=7, color="#666", zorder=6)
    _arrow(ax, adn["r"], y_main, pel["l"], y_main, r"$V_{TEC}/I_{TEC}$")
    _arrow(ax, pel["r"], y_main, s2["l"], y_main, r"$Q_{cool}$")
    _arrow(ax, s2["r"], y_main, thm["l"], y_main, r"$Q_{net}$")

    # 熱系出力 T（右へ）→ フィードバックへ折り返し
    t_node_x = 17.55
    _arrow(ax, thm["r"], y_main, t_node_x, y_main, "T (温度)")
    _line(ax, [t_node_x, t_node_x], [y_main, y_fb])
    _arrow(ax, t_node_x, y_fb, sen["r"], y_fb)

    # フィードバック（右→左）
    _arrow(ax, sen["l"], y_fb, adc["r"], y_fb, "電圧 V")
    _line(ax, [adc["l"], s1["cx"]], [y_fb, y_fb])
    _arrow(ax, s1["cx"], y_fb, s1["cx"], s1["b"], "測定ADC",
           lx=s1["cx"] + 1.0, ly=(y_fb + s1["b"]) / 2)

    # --- 外乱 Q_laser の注入 ---
    dist_y = y_main + 1.55
    ax.text(s2["cx"], dist_y + 0.28, "外乱：レーザー発熱",
            ha="center", va="center", fontsize=8.5, color="#b5651d")
    ax.text(s2["cx"], dist_y - 0.02, f"$Q_{{laser}}$ = 0〜{2:g} W",
            ha="center", va="center", fontsize=8.5, color="#b5651d")
    _arrow(ax, s2["cx"], dist_y - 0.35, s2["cx"], s2["t"])

    # --- 加算点の符号（順作用: e = 目標 − 測定）---
    ax.text(s1["l"] - 0.18, y_main + 0.30, "+", ha="center", va="center",
            fontsize=13, fontweight="bold", color="#c0392b")
    ax.text(s1["cx"] + 0.28, s1["b"] + 0.30, "−", ha="center", va="center",
            fontsize=13, fontweight="bold", color="#c0392b")
    ax.text(s2["l"] - 0.18, y_main + 0.30, "+", ha="center", va="center",
            fontsize=12, fontweight="bold", color="#27ae60")
    ax.text(s2["cx"] + 0.30, s2["t"] - 0.05, "+", ha="center", va="center",
            fontsize=12, fontweight="bold", color="#27ae60")

    # --- タイトルと注記 ---
    ax.text(9.0, 7.6, "レーザー温度制御 PID フィードバックループ",
            ha="center", va="center", fontsize=13, fontweight="bold")
    ax.text(9.0, 0.5,
            "※ 制御量は ADC コード（温度換算せず）。順作用 PID（e = 目標 − 測定）。"
            "指令電圧=OUT2(0〜2.5V)。V_TEC=5·(VREF/2−OUT2) を Vlim/Ilim・負荷線・VDD で制限"
            "（方向別に比率クランプ可）。",
            ha="center", va="center", fontsize=8.5, color="#555")

    fig.tight_layout()
    return fig
