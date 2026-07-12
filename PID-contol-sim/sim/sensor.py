"""センサ経路：温度 → サーミスタ抵抗 → 分圧電圧 → 16bit ADC コード。

ADC コードは温度に換算せず、そのまま PID の制御量として使う。
"""
import math

from config import ThermistorConfig, AdcDacConfig

_KELVIN = 273.15


class Sensor:
    def __init__(self, thermistor: ThermistorConfig, adc: AdcDacConfig):
        self.th = thermistor
        self.adc = adc

    def resistance(self, temp_c: float) -> float:
        """温度 [℃] における NTC サーミスタ抵抗 [Ω]。"""
        t = temp_c + _KELVIN
        t25 = self.th.t25_c + _KELVIN
        return self.th.r25 * math.exp(self.th.b_const * (1.0 / t - 1.0 / t25))

    def voltage(self, temp_c: float) -> float:
        """IN1N に入る分圧電圧 [V]（サーミスタを上側にした分圧）。

        温度↑ → 抵抗↓ → 電圧↑ の単調な向きにしておく。
        """
        r_ntc = self.resistance(temp_c)
        return self.th.vref * self.th.r_fixed1 / (r_ntc + self.th.r_fixed2) * 2

    def adc_code(self, temp_c: float) -> int:
        """温度 [℃] を 16bit ADC コード（0〜65535）に変換する。"""
        v = self.voltage(temp_c)
        code = round(v / self.adc.vref * self.adc.max_code)
        return max(0, min(self.adc.max_code, code))
