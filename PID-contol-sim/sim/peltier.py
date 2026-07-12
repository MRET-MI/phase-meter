"""操作経路：PID 出力 → 16bit DAC → 指令電圧(OUT2) → TEC 電圧/電流 → 冷却パワー。

ADN8834 の実機関係に合わせる：
- 指令電圧 = OUT2 ピンへ入力する電圧 Vout2 = DACコード/フルスケール × VREF（0〜VREF、中点 VREF/2 が無駆動）。
- ペルチェ電圧 V_TEC = V_LDR − V_SFB = 5·(VREF/2 − Vout2)（差動出力段の固定ゲイン5）。
  → OUT2 を中点より下げると冷却（V_TEC>0）、上げると加熱（V_TEC<0）。
- V_TEC は ADN8834 の実効最大（負荷線 min(Vlim, Ilim·R, VDD)）でクランプ。
- 指令比率クランプ（冷却/加熱 各0〜1）は OUT2 の振れ幅を制限（1で 0V / VREF まで）。
"""
from config import PeltierConfig, AdcDacConfig, TecDriverConfig
import tecdriver

_GAIN_OUT2 = 5.0  # ADN8834 差動出力段の固定ゲイン（V_TEC = 5·(VREF/2 − Vout2)）


class Peltier:
    def __init__(self, peltier: PeltierConfig, adc: AdcDacConfig, tec: TecDriverConfig):
        self.pl = peltier
        self.adc = adc
        self.tec = tec
        self.mid_code = (self.adc.max_code + 1) // 2  # 中央コード（無駆動）
        self.refresh_limits()

    def refresh_limits(self):
        """TEC ドライバの実効最大電圧（負荷線＋VDD）を再計算してキャッシュ。"""
        eff = tecdriver.effective_max(self.tec, self.pl)
        self.veff_cool = eff["veff_cool"]
        self.veff_heat = eff["veff_heat"]

    def quantize_dac(self, pid_output: float) -> int:
        """PID 出力（双極性コード相当）を 16bit DAC の実コードに量子化する。"""
        code = round(self.mid_code + pid_output)
        return max(0, min(self.adc.max_code, code))

    def out2_voltage(self, dac_code: int) -> float:
        """指令電圧 = OUT2 ピン電圧 [V]（0〜VREF、中点=VREF/2）。指令比率クランプ適用。"""
        center = self.adc.vref / 2.0
        raw = dac_code / self.adc.max_code * self.adc.vref
        out2_min = center * (1.0 - self.tec.cmd_ratio_cool)  # 冷却側の下限
        out2_max = center * (1.0 + self.tec.cmd_ratio_heat)  # 加熱側の上限
        return max(out2_min, min(out2_max, raw))

    # 「指令電圧」の別名（= OUT2 電圧）
    def command_voltage(self, dac_code: int) -> float:
        return self.out2_voltage(dac_code)

    def tec_voltage(self, dac_code: int) -> float:
        """ペルチェ電圧 V_TEC [V]（+=冷却）= 5·(VREF/2 − Vout2)。実効最大でクランプ。"""
        center = self.adc.vref / 2.0
        v_req = _GAIN_OUT2 * (center - self.out2_voltage(dac_code))
        return max(-self.veff_heat, min(self.veff_cool, v_req))

    def current(self, dac_code: int) -> float:
        """ペルチェ電流 [A]（双極性）。I = V_TEC / R。"""
        r = self.pl.r_elec
        if r <= 0.0:
            return 0.0
        return self.tec_voltage(dac_code) / r

    def cooling_power(self, dac_code: int) -> float:
        """冷却パワー [W]（正=冷却）。Q = k_pelt·V_TEC（±q_max で飽和）。"""
        v = self.tec_voltage(dac_code)
        q = self.pl.k_pelt * v
        return max(-self.pl.q_max, min(self.pl.q_max, q))
