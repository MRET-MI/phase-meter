"""離散 PID コントローラ。制御量は ADC コードそのもの（温度換算しない）。

出力クランプと、飽和時に積分を止めるアンチワインドアップを備える。
NTC＋冷却の逆特性を吸収するため reverse（逆作用）に対応する。
"""
from config import PidConfig


class PID:
    def __init__(self, cfg: PidConfig):
        self.cfg = cfg
        self.reset()

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._has_prev = False

    def update_gains(self, kp: float, ki: float, kd: float):
        """GUI からのゲイン変更を反映する。"""
        self.cfg.kp = kp
        self.cfg.ki = ki
        self.cfg.kd = kd

    def compute(self, setpoint: float, measurement: float, dt: float) -> float:
        """setpoint と measurement（ともに ADC コード）から PID 出力を返す。

        reverse=True（逆作用）では error=measurement-setpoint とし、
        「温度が目標より高い（ADC が大きい）→ 出力を増やして冷却」を成立させる。
        """
        if self.cfg.reverse:
            error = measurement - setpoint
        else:
            error = setpoint - measurement

        # 微分項（初回は 0）
        if self._has_prev and dt > 0.0:
            derivative = (error - self._prev_error) / dt
        else:
            derivative = 0.0

        # 積分項の暫定更新
        integral = self._integral + error * dt

        out = self.cfg.kp * error + self.cfg.ki * integral + self.cfg.kd * derivative

        # 出力飽和 + アンチワインドアップ（飽和方向へ押す積分は採用しない）
        clamped = max(self.cfg.out_min, min(self.cfg.out_max, out))
        if clamped == out or (error > 0) != (integral > 0):
            self._integral = integral  # 飽和していない、または積分が飽和を解く向き

        self._prev_error = error
        self._has_prev = True
        return clamped
