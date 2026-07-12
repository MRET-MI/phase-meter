"""負荷側の熱モデル（1次遅れ）を python-control の状態空間で表現する。

  C·dT/dt = -(T - Ta)/Rth + Q_net
  Q_net = Q_laser - Q_cool   （正味の加熱パワー [W]）

状態 x = T - Ta（周囲基準の温度差）とすると:
  dx/dt = -1/(Rth·C)·x + (1/C)·Q_net
逐次シミュレーションのため、状態を保持して forced_response で1ステップずつ進める。
"""
import control
import numpy as np

from config import ThermalConfig


class ThermalModel:
    def __init__(self, cfg: ThermalConfig):
        self.cfg = cfg
        c = cfg.heat_capacity
        rth = cfg.r_thermal
        # 1次系の状態空間: A=-1/(Rth·C), B=1/C, C=1, D=0（出力は温度差 x）
        a = [[-1.0 / (rth * c)]]
        b = [[1.0 / c]]
        cc = [[1.0]]
        d = [[0.0]]
        self.sys = control.ss(a, b, cc, d)
        self.reset()

    def reset(self):
        """状態を初期温度に戻す。"""
        # 状態 x = T - Ta
        self.x = float(self.cfg.init_c - self.cfg.ambient_c)

    @property
    def temperature(self) -> float:
        """現在温度 [℃]。"""
        return self.x + self.cfg.ambient_c

    def step(self, dt: float, q_net: float) -> float:
        """正味加熱パワー q_net [W] を dt 秒印加し、温度 [℃] を返す。"""
        t_span = [0.0, dt]
        u = [q_net, q_net]
        res = control.forced_response(self.sys, T=t_span, U=u, X0=[self.x])
        self.x = float(np.atleast_1d(res.states[..., -1])[-1])
        return self.temperature
