"""PID オートチューン（プラント同定＋IMC 整定）。

開ループのステップ応答から1次遅れプラントの K・τ を推定し、
IMC/λ 法で PID（実質 PI）ゲインを算出する。GUI の「整定」タブから使う。
"""
from config import SimConfig
from sim.sensor import Sensor
from sim.peltier import Peltier
from sim.thermal import ThermalModel


def _time_to_reach(ts, ys, y0, yinf):
    """63.2% 到達時刻（時定数 τ）を線形補間で求める。"""
    target = y0 + 0.632 * (yinf - y0)
    rising = yinf >= y0
    for i in range(1, len(ys)):
        prev, cur = ys[i - 1], ys[i]
        crossed = (cur >= target) if rising else (cur <= target)
        if crossed:
            # (prev→cur) の間で線形補間
            if cur == prev:
                return ts[i]
            frac = (target - prev) / (cur - prev)
            return ts[i - 1] + frac * (ts[i] - ts[i - 1])
    return ts[-1]


def identify(cfg: SimConfig, u_step: float, dt: float = 0.1,
             duration: float = None) -> dict:
    """開ループステップ応答でプラント（u→ADC）を同定する。

    u_step: PID 出力相当の双極性コード（正=冷却方向）。
    戻り値: ts, ys, y0, yinf, K, tau, saturated など。
    """
    sensor = Sensor(cfg.thermistor, cfg.adc)
    peltier = Peltier(cfg.peltier, cfg.adc, cfg.tec)
    thermal = ThermalModel(cfg.thermal)
    thermal.reset()

    tau_guess = cfg.thermal.r_thermal * cfg.thermal.heat_capacity
    if duration is None:
        duration = max(5.0 * tau_guess, 20.0 * dt)
    n = max(2, int(duration / dt))

    dac_code = peltier.quantize_dac(u_step)
    q_cool = peltier.cooling_power(dac_code)
    # 飽和判定：要求 V_TEC が実効最大/クランプで頭打ちなら線形同定にならない
    center = cfg.adc.vref / 2.0
    v_req = 5.0 * (center - peltier.out2_voltage(dac_code))
    v_act = peltier.tec_voltage(dac_code)
    saturated = abs(v_act) < abs(v_req) - 1e-6

    y0 = sensor.adc_code(thermal.temperature)  # ステップ前の基準
    ts, ys = [0.0], [y0]
    for i in range(1, n + 1):
        # 開ループ：外乱なし、固定の冷却を印加
        temp = thermal.step(dt, 0.0 - q_cool)
        ts.append(i * dt)
        ys.append(sensor.adc_code(temp))

    yinf = ys[-1]
    K = (yinf - y0) / u_step if u_step != 0 else 0.0
    tau = _time_to_reach(ts, ys, y0, yinf)
    return dict(ts=ts, ys=ys, y0=y0, yinf=yinf, K=K, tau=tau,
                dac_code=dac_code, v_tec=peltier.tec_voltage(dac_code),
                q_cool=q_cool, saturated=saturated)


def imc_pi(K: float, tau: float, lam: float) -> tuple:
    """IMC/λ 法で PI ゲインを算出する（Kd=0）。

    Kc = τ / (|K|·λ),  Ti = τ,  Ki = Kc/Ti。むだ時間なしの1次遅れ向け。
    戻り値: (kp, ki, kd)
    """
    if K == 0 or lam <= 0 or tau <= 0:
        return 0.0, 0.0, 0.0
    kc = tau / (abs(K) * lam)
    ti = tau
    ki = kc / ti
    return kc, ki, 0.0
