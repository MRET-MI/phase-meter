"""逐次シミュレータ：センサ→ADC→PID→DAC→ペルチェ→熱系 を1ステップ統合する。

GUI の QTimer から step() を周期的に呼ぶ。履歴を保持しグラフ描画に使う。
"""
from collections import deque
from dataclasses import dataclass

from config import SimConfig
from sim.sensor import Sensor
from sim.peltier import Peltier
from sim.thermal import ThermalModel
from sim.pid import PID


@dataclass
class SimSample:
    """1ステップの記録。"""
    t: float
    temp_c: float
    adc_code: int
    setpoint_code: int
    dac_code: int
    cmd_v: float       # 指令電圧 = OUT2 ピン電圧 [V]（0〜VREF、中点=無駆動）
    v_tec: float       # ペルチェ電圧 V_TEC [V]（= V_LDR − V_SFB = 5·(VREF/2 − OUT2)）
    peltier_i: float   # ペルチェ電流 [A]
    q_cool: float
    laser_w: float


class Simulator:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.sensor = Sensor(cfg.thermistor, cfg.adc)
        self.peltier = Peltier(cfg.peltier, cfg.adc, cfg.tec)
        self.thermal = ThermalModel(cfg.thermal)
        self.pid = PID(cfg.pid)
        maxlen = max(1, int(cfg.history_seconds / cfg.dt))
        self.history: deque = deque(maxlen=maxlen)
        self.reset()

    def reset(self):
        """時刻・状態・履歴をすべて初期化する。"""
        self.t = 0.0
        self.thermal.reset()
        self.pid.reset()
        self.history.clear()

    @property
    def setpoint_code(self) -> int:
        """目標温度に対応する ADC コード（制御の目標値）。"""
        return self.sensor.adc_code(self.cfg.target_c)

    def step(self) -> SimSample:
        """1制御周期を進め、記録を返す。"""
        dt = self.cfg.dt

        # 1) センサ：現在温度 → ADC コード（制御量）
        temp = self.thermal.temperature
        adc = self.sensor.adc_code(temp)
        setpoint = self.setpoint_code

        # 2) PID → 3) DAC 量子化 → ペルチェ冷却パワー
        pid_out = self.pid.compute(setpoint, adc, dt)
        dac_code = self.peltier.quantize_dac(pid_out)
        cmd_v = self.peltier.command_voltage(dac_code)
        v_tec = self.peltier.tec_voltage(dac_code)
        peltier_i = self.peltier.current(dac_code)
        q_cool = self.peltier.cooling_power(dac_code)

        # 4) 熱系更新（正味加熱 = 外乱発熱 - 冷却）
        q_net = self.cfg.laser_power - q_cool
        new_temp = self.thermal.step(dt, q_net)

        # 5) 記録
        sample = SimSample(
            t=self.t, temp_c=new_temp, adc_code=adc, setpoint_code=setpoint,
            dac_code=dac_code, cmd_v=cmd_v, v_tec=v_tec,
            peltier_i=peltier_i, q_cool=q_cool, laser_w=self.cfg.laser_power,
        )
        self.history.append(sample)
        self.t += dt
        return sample
