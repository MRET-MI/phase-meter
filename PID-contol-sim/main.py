"""レーザー温度制御 PID シミュレータの GUI エントリ。

ui/main_window.ui（pyside6-designer で編集可能）を読み込み、
pyqtgraph のグラフを埋め込み、QTimer で逐次シミュレーションを回す。
"""
import os
import sys

# matplotlib(Qt バックエンド) が PySide6 を使うよう、読込前に指定する
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QWidget, QPushButton, QDoubleSpinBox, QLabel,
    QCheckBox,
)
from PySide6.QtCore import QTimer, QFile, Qt
from PySide6.QtUiTools import QUiLoader
import pyqtgraph as pg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from config import default_config
from sim.simulator import Simulator
from blockdiagram import build_figure
from characteristics import build_figure as build_char_figure
import autotune
import tecdriver
import teclimitplot

_UI_PATH = os.path.join(os.path.dirname(__file__), "ui", "main_window.ui")


def load_ui(path: str):
    """QUiLoader で .ui を読み込みウィジェットを返す。"""
    loader = QUiLoader()
    f = QFile(path)
    f.open(QFile.ReadOnly)
    win = loader.load(f)
    f.close()
    return win


class SimApp:
    def __init__(self):
        self.cfg = default_config()
        self.sim = Simulator(self.cfg)

        self.win = load_ui(_UI_PATH)
        self._bind_widgets()

        # QTimer で逐次実行（ハンドラより先に用意する）
        self.timer = QTimer(self.win)
        self.timer.timeout.connect(self._on_tick)

        self._rec_gains = None  # 直近の推奨ゲイン (kp, ki, kd)

        self._embed_plots()
        self._embed_block_diagram()
        self._embed_characteristics()
        self._embed_ident_plot()
        self._embed_teclimit_plot()
        self._connect_signals()
        self._sync_config_from_ui()

    # ---- ウィジェット取得（findChild で確実に）----
    def _bind_widgets(self):
        w = self.win
        self.btnStart = w.findChild(QPushButton, "btnStart")
        self.btnStop = w.findChild(QPushButton, "btnStop")
        self.btnReset = w.findChild(QPushButton, "btnReset")
        self.spinKp = w.findChild(QDoubleSpinBox, "spinKp")
        self.spinKi = w.findChild(QDoubleSpinBox, "spinKi")
        self.spinKd = w.findChild(QDoubleSpinBox, "spinKd")
        self.spinTarget = w.findChild(QDoubleSpinBox, "spinTarget")
        self.spinLaser = w.findChild(QDoubleSpinBox, "spinLaser")
        self.spinDt = w.findChild(QDoubleSpinBox, "spinDt")
        self.lblTime = w.findChild(QLabel, "lblTime")
        self.lblTemp = w.findChild(QLabel, "lblTemp")
        self.lblAdc = w.findChild(QLabel, "lblAdc")
        self.lblDac = w.findChild(QLabel, "lblDac")
        self.lblQ = w.findChild(QLabel, "lblQ")
        # 整定（オートチューン）タブ
        self.spinStepU = w.findChild(QDoubleSpinBox, "spinStepU")
        self.spinLambda = w.findChild(QDoubleSpinBox, "spinLambda")
        self.btnIdentify = w.findChild(QPushButton, "btnIdentify")
        self.btnApplyGains = w.findChild(QPushButton, "btnApplyGains")
        self.lblK = w.findChild(QLabel, "lblK")
        self.lblTau = w.findChild(QLabel, "lblTau")
        self.lblSat = w.findChild(QLabel, "lblSat")
        self.lblRecKp = w.findChild(QLabel, "lblRecKp")
        self.lblRecKi = w.findChild(QLabel, "lblRecKi")
        self.lblRecKd = w.findChild(QLabel, "lblRecKd")
        # TECリミット タブ
        self.spinRatioCool = w.findChild(QDoubleSpinBox, "spinRatioCool")
        self.spinRatioHeat = w.findChild(QDoubleSpinBox, "spinRatioHeat")
        self.btnApplyRecommend = w.findChild(QPushButton, "btnApplyRecommend")
        self.lblTecTable = w.findChild(QLabel, "lblTecTable")
        # 下段プロットの表示選択
        self.chkCmdV = w.findChild(QCheckBox, "chkCmdV")
        self.chkVtec = w.findChild(QCheckBox, "chkVtec")
        self.chkCurrent = w.findChild(QCheckBox, "chkCurrent")

        # 入力は Enter（または確定）で反映：キーボード入力の逐次発火を止める
        for spin in (self.spinKp, self.spinKi, self.spinKd,
                     self.spinTarget, self.spinLaser, self.spinDt):
            spin.setKeyboardTracking(False)

    # ---- グラフ埋め込み ----
    def _embed_plots(self):
        pg.setConfigOptions(antialias=True)

        self.plot_temp = pg.PlotWidget()
        self.plot_temp.setLabel("left", "温度", units="℃")
        self.plot_temp.setLabel("bottom", "時間", units="s")
        self.plot_temp.showGrid(x=True, y=True, alpha=0.3)
        self.plot_temp.addLegend(offset=(10, 10))
        self.plot_temp.setYRange(15, 35)  # 初期表示範囲 [℃]
        self.curve_temp = self.plot_temp.plot(
            pen=pg.mkPen("#e06c75", width=2), name="温度")
        self.curve_target = self.plot_temp.plot(
            pen=pg.mkPen("#61afef", width=1, style=Qt.DashLine), name="目標")

        self.plot_sig = pg.PlotWidget()
        self.plot_sig.setLabel("left", "パワー", units="W")
        self.plot_sig.setLabel("bottom", "時間", units="s")
        self.plot_sig.showGrid(x=True, y=True, alpha=0.3)
        self.plot_sig.addLegend(offset=(10, 10))
        self.plot_sig.setYRange(-5, 5)  # 初期表示範囲 [W]
        self.curve_qcool = self.plot_sig.plot(
            pen=pg.mkPen("#98c379", width=2), name="冷却パワー")
        self.curve_laser = self.plot_sig.plot(
            pen=pg.mkPen("#e5c07b", width=1, style=Qt.DashLine), name="外乱(レーザー)")

        self._embed_vi_plot()

        self._put_in_container("plotTemp", self.plot_temp)
        self._put_in_container("plotSignal", self.plot_sig)
        self._put_in_container("plotVI", self.plot_vi)

    def _embed_vi_plot(self):
        """Temperature Set 電圧（左軸）とペルチェ電流（右軸）の2軸プロット。"""
        self.plot_vi = pg.PlotWidget()
        pi = self.plot_vi.getPlotItem()
        pi.setLabel("bottom", "時間", units="s")
        pi.setLabel("left", "電圧", units="V", color="#56b6c2")
        pi.showGrid(x=True, y=True, alpha=0.3)
        self.vi_legend = pi.addLegend(offset=(10, 10))
        self.curve_vset = pi.plot(pen=pg.mkPen("#56b6c2", width=2))
        self.curve_vtec = pi.plot(pen=pg.mkPen("#e06c75", width=2))

        # 右軸（ペルチェ電流）用の独立 ViewBox
        self.vb_i = pg.ViewBox()
        pi.showAxis("right")
        pi.scene().addItem(self.vb_i)
        pi.getAxis("right").linkToView(self.vb_i)
        pi.getAxis("right").setLabel("ペルチェ電流", units="A", color="#d19a66")
        self.vb_i.setXLink(pi)
        self.curve_i = pg.PlotCurveItem(
            pen=pg.mkPen("#d19a66", width=2, style=Qt.DashLine))
        self.vb_i.addItem(self.curve_i)

        def _update_vb_geom():
            self.vb_i.setGeometry(pi.vb.sceneBoundingRect())
            self.vb_i.linkedViewChanged(pi.vb, self.vb_i.XAxis)

        self._update_vb_geom = _update_vb_geom
        pi.vb.sigResized.connect(_update_vb_geom)
        _update_vb_geom()

        # 初期表示範囲：左=電圧 −3.3〜3.3V、右=電流は 0 を揃えて対称に
        self.plot_vi.setYRange(-3.3, 3.3)
        self.vb_i.setYRange(-2.0, 2.0)

    def _put_in_container(self, name: str, widget):
        container = self.win.findChild(QWidget, name)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    # ---- ブロック図の埋め込み ----
    def _embed_block_diagram(self):
        fig = build_figure(self.cfg)
        self.block_canvas = FigureCanvas(fig)
        self._put_in_container("blockDiagramContainer", self.block_canvas)

    # ---- 特性グラフの埋め込み ----
    def _embed_characteristics(self):
        fig = build_char_figure(self.cfg)
        self.char_canvas = FigureCanvas(fig)
        self._put_in_container("charContainer", self.char_canvas)

    # ---- 同定ステップ応答グラフの埋め込み ----
    def _embed_ident_plot(self):
        self.plot_ident = pg.PlotWidget()
        self.plot_ident.setLabel("left", "ADC値", units="code")
        self.plot_ident.setLabel("bottom", "時間", units="s")
        self.plot_ident.showGrid(x=True, y=True, alpha=0.3)
        self.plot_ident.addLegend()
        self.curve_ident = self.plot_ident.plot(
            pen=pg.mkPen("#e06c75", width=2), name="開ループ応答")
        self.curve_ident63 = self.plot_ident.plot(
            pen=pg.mkPen("#61afef", width=1, style=Qt.DashLine), name="63% / τ")
        self._put_in_container("plotIdent", self.plot_ident)

    # ---- TECリミット V–I 図の埋め込み ----
    def _embed_teclimit_plot(self):
        self.teclimit_fig = Figure(figsize=(5.5, 4.5))
        self.teclimit_canvas = FigureCanvas(self.teclimit_fig)
        self._put_in_container("plotTecLimit", self.teclimit_canvas)
        teclimitplot.draw(self.teclimit_fig, self.cfg)

    def _update_teclimit_plot(self):
        teclimitplot.draw(self.teclimit_fig, self.cfg)
        self.teclimit_canvas.draw_idle()

    # ---- シグナル接続 ----
    def _connect_signals(self):
        self.btnStart.clicked.connect(self._on_start)
        self.btnStop.clicked.connect(self._on_stop)
        self.btnReset.clicked.connect(self._on_reset)
        self.spinKp.valueChanged.connect(self._on_gain_changed)
        self.spinKi.valueChanged.connect(self._on_gain_changed)
        self.spinKd.valueChanged.connect(self._on_gain_changed)
        self.spinTarget.valueChanged.connect(self._on_target_changed)
        self.spinLaser.valueChanged.connect(self._on_laser_changed)
        self.spinDt.valueChanged.connect(self._on_dt_changed)
        self.btnIdentify.clicked.connect(self._on_identify)
        self.btnApplyGains.clicked.connect(self._on_apply_gains)
        self.spinRatioCool.valueChanged.connect(self._on_ratio_changed)
        self.spinRatioHeat.valueChanged.connect(self._on_ratio_changed)
        self.btnApplyRecommend.clicked.connect(self._on_apply_recommend)
        for chk in (self.chkCmdV, self.chkVtec, self.chkCurrent):
            chk.toggled.connect(self._on_vi_select)

    def _sync_config_from_ui(self):
        """起動時に UI 値を config へ反映する。"""
        self._on_gain_changed()
        self._on_target_changed()
        self._on_laser_changed()
        self._on_dt_changed()
        self._on_ratio_changed()
        self._on_vi_select()

    def _on_vi_select(self, *_):
        """下段プロットの表示曲線と凡例をチェックボックスで切り替える。"""
        items = (
            (self.chkCmdV, self.curve_vset, "指令電圧(OUT2)"),
            (self.chkVtec, self.curve_vtec, "V_TEC"),
            (self.chkCurrent, self.curve_i, "ペルチェ電流"),
        )
        self.vi_legend.clear()
        for chk, curve, name in items:
            visible = chk.isChecked()
            curve.setVisible(visible)
            if visible:
                self.vi_legend.addItem(curve, name)

    # ---- ハンドラ ----
    def _on_start(self):
        self.timer.start(max(10, int(self.cfg.dt * 1000)))

    def _on_stop(self):
        self.timer.stop()

    def _on_reset(self):
        self.timer.stop()
        self.sim.reset()
        self._redraw()

    def _on_gain_changed(self, *_):
        self.sim.pid.update_gains(
            self.spinKp.value(), self.spinKi.value(), self.spinKd.value())

    def _on_target_changed(self, *_):
        self.cfg.target_c = self.spinTarget.value()

    def _on_laser_changed(self, *_):
        self.cfg.laser_power = self.spinLaser.value()

    def _on_dt_changed(self, *_):
        self.cfg.dt = self.spinDt.value()
        if self.timer.isActive():
            self.timer.start(max(10, int(self.cfg.dt * 1000)))

    # ---- オートチューン（同定＋IMC）----
    def _on_identify(self):
        """開ループステップ応答でプラントを同定し、IMC 推奨ゲインを算出・表示する。"""
        u_step = self.spinStepU.value()
        lam = self.spinLambda.value()
        res = autotune.identify(self.cfg, u_step)
        kp, ki, kd = autotune.imc_pi(res["K"], res["tau"], lam)
        self._rec_gains = (kp, ki, kd)

        # 結果表示
        self.lblK.setText(f"{res['K']:.4g} code/code")
        self.lblTau.setText(f"{res['tau']:.2f}")
        self.lblSat.setText("飽和（u を下げてください）" if res["saturated"] else "線形域 OK")
        self.lblRecKp.setText(f"{kp:.4g}")
        self.lblRecKi.setText(f"{ki:.4g}")
        self.lblRecKd.setText(f"{kd:.4g}")

        # ステップ応答グラフ
        ts, ys = res["ts"], res["ys"]
        self.curve_ident.setData(ts, ys)
        y63 = res["y0"] + 0.632 * (res["yinf"] - res["y0"])
        tau = res["tau"]
        self.curve_ident63.setData([0, tau, tau], [y63, y63, res["yinf"]])

    def _on_apply_gains(self):
        """推奨ゲインを PID とシミュレータタブの入力欄へ反映する。"""
        if self._rec_gains is None:
            return
        kp, ki, kd = self._rec_gains
        self.spinKp.setValue(kp)
        self.spinKi.setValue(ki)
        self.spinKd.setValue(kd)  # valueChanged → _on_gain_changed で PID へ反映

    # ---- TECリミット（クランプ比率）----
    def _on_ratio_changed(self, *_):
        self.cfg.tec.cmd_ratio_cool = self.spinRatioCool.value()
        self.cfg.tec.cmd_ratio_heat = self.spinRatioHeat.value()
        self._update_tec_table()

    def _on_apply_recommend(self):
        r_cool, r_heat = tecdriver.recommended_ratios(self.cfg.tec, self.cfg.peltier)
        self.spinRatioCool.setValue(r_cool)
        self.spinRatioHeat.setValue(r_heat)  # valueChanged → _on_ratio_changed

    def _update_tec_table(self):
        ev = tecdriver.evaluate(self.cfg.tec, self.cfg.peltier)
        self.lblTecTable.setText(self._tec_table_html(ev))
        self._update_teclimit_plot()

    def _tec_table_html(self, ev):
        def ok(b):
            return ('<span style="color:#2e7d32">✅</span>' if b
                    else '<span style="color:#c62828">❌</span>')

        def row(d):
            return (
                f"<tr><td><b>{d['name']}</b></td>"
                f"<td align=right>{d['vlim']:.2f}</td>"
                f"<td align=right>{d['ilim']:.2f}</td>"
                f"<td align=right>{d['veff']:.2f} ({d['binding']})</td>"
                f"<td align=right>{d['ieff']:.2f}</td>"
                f"<td align=right>{d['ratio']:.2f}</td>"
                f"<td align=right>{d['vcmd']:.2f}</td>"
                f"<td align=right>{d['v_tec']:.2f}</td>"
                f"<td align=right>{d['i_tec']:.2f}</td>"
                f"<td align=center>{ok(d['v_ok'])}</td>"
                f"<td align=center>{ok(d['i_ok'])}</td>"
                f"<td align=right><b>{d['rec']:.2f}</b></td></tr>"
            )

        tec = self.cfg.tec
        pl = self.cfg.peltier
        derate = tec.derate
        head = (
            f"<div>定格×{derate:g} 上限：V ≤ {ev['vsafe']:.2f} V "
            f"(= Vmax {pl.v_rating:g}V × {derate:g}), "
            f"I ≤ {ev['isafe']:.2f} A (= Imax {pl.i_rating:g}A × {derate:g})"
            f"　／　指令電圧 範囲 0〜{ev['vref']:g} V（中点 {ev['vcmd_center']:.2f}V = 無駆動）</div><br>"
        )
        table = (
            "<table border=1 cellspacing=0 cellpadding=5>"
            "<tr>"
            "<th>方向</th><th> ADN8834 <br>Vlim[V]</th><th> ADN8834 <br>Ilim[A]</th>"
            "<th>実効最大V[V]<br>(律速)</th><th>実効最大I[A]</th>"
            "<th>指令比率</th><th>指令電圧<br>[V]</th>"
            "<th> V_TEC <br>[V]</th><th> I_TEC <br>[A]</th>"
            "<th> V判定 <br>(×0.7)</th><th> I判定 <br>(×0.7)</th><th>推奨比率</th>"
            "</tr>"
            + row(ev["cool"]) + row(ev["heat"]) +
            "</table>"
        )
        legend = (
            "<br><div><b>各項目の説明</b></div>"
            "<ul>"
            "<li><b>方向</b>：冷却＝ペルチェで吸熱、加熱＝放熱。ADN8834 は方向で"
            "リミットが非対称（電流シンクにより加熱側が低くなる）。</li>"
            "<li><b>ADN8834 Vlim / Ilim</b>：分圧抵抗（Rv1/Rv2, Rc1/Rc2）で決まる"
            "ハード上限。TEC 電圧・電流がこれを超えないようドライバが制限する。</li>"
            "<li><b>実効最大 V / I（律速）</b>：負荷線 V=I×R（R="
            f"{pl.r_elec:g}Ω）と VDD（{tec.vdd:g}V）を考慮した実際に到達できる最大。"
            "<code>min(Vlim, Ilim×R, VDD)</code>。括弧内が律速要因（Vlim/Ilim/VDD）。</li>"
            "<li><b>指令比率</b>：ソフト側で与える OUT2 振れ幅の割合（0〜1、方向別）。"
            "1 で OUT2 を 0V/VREF まで振る（＝実効最大まで駆動）、0 で無駆動。</li>"
            "<li><b>指令電圧(OUT2)</b>：ADN8834 の OUT2 へ入力する電圧（絶対値 0〜"
            f"{tec.vref:g}V、中点 {tec.vref / 2:g}V=無駆動）。V_TEC=5·(中点−OUT2) なので"
            f"冷却は中点から下げ・加熱は上げ、比率1 で 冷却→0V / 加熱→{tec.vref:g}V。</li>"
            "<li><b>V_TEC / I_TEC</b>：その比率での TEC 電圧・電流。"
            "<code>V_TEC=5·(中点−OUT2)</code> を実効最大で飽和させた値、I_TEC=V_TEC/R。"
            "ゲイン5 のため小さな OUT2 振れでも実効最大に達しやすい。</li>"
            "<li><b>V判定 / I判定（×0.7）</b>：V_TEC・I_TEC が定格×0.7 以内なら ✅、"
            "超過なら ❌。安全マージン確保の可否。</li>"
            "<li><b>推奨比率</b>：定格×0.7（V,I とも）に収まる最大の指令比率。"
            "実効最大が安全上限以下なら 1.0、超える方向は OUT2 振れを"
            "<code>安全V_TEC/(5·中点)</code> までに制限した値。「推奨値を適用」で設定。</li>"
            "</ul>"
        )
        return head + table + legend

    # ---- 逐次実行と描画 ----
    def _on_tick(self):
        self.sim.step()
        self._redraw()

    def _redraw(self):
        hist = self.sim.history
        ts = [s.t for s in hist]
        temps = [s.temp_c for s in hist]
        qcools = [s.q_cool for s in hist]
        lasers = [s.laser_w for s in hist]
        vsets = [s.cmd_v for s in hist]
        vtecs = [s.v_tec for s in hist]
        currents = [s.peltier_i for s in hist]

        self.curve_temp.setData(ts, temps)
        if ts:
            self.curve_target.setData([ts[0], ts[-1]],
                                      [self.cfg.target_c, self.cfg.target_c])
        else:
            self.curve_target.setData([], [])
        self.curve_qcool.setData(ts, qcools)
        self.curve_laser.setData(ts, lasers)

        # 指令電圧(OUT2)・V_TEC（左軸）とペルチェ電流（右軸）
        self.curve_vset.setData(ts, vsets)
        self.curve_vtec.setData(ts, vtecs)
        self.curve_i.setData(ts, currents)

        self._update_status(hist[-1] if hist else None)

    def _update_status(self, s):
        if s is None:
            for lbl in (self.lblTime, self.lblTemp, self.lblAdc, self.lblDac, self.lblQ):
                lbl.setText("-")
            return
        self.lblTime.setText(f"{s.t:.1f}")
        self.lblTemp.setText(f"{s.temp_c:.3f}")
        self.lblAdc.setText(f"{s.adc_code} / {s.setpoint_code}")
        self.lblDac.setText(f"{s.dac_code}  (指令 {s.cmd_v:.3f} V)")
        self.lblQ.setText(f"{s.q_cool:+.3f}")

    def show(self):
        self.win.show()


def main():
    app = QApplication(sys.argv)
    sim_app = SimApp()
    sim_app.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
