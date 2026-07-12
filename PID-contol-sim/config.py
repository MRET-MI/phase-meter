"""レーザー温度制御 PID シミュレータの代表値パラメータ。

すべて代表値。GUI やこのファイルで後から調整可能。
"""
from dataclasses import dataclass


@dataclass
class ThermistorConfig:
    """サーミスタ（NTC）と分圧回路の設定。"""
    r25: float = 10_000.0        # 25℃ での抵抗 [Ω]
    b_const: float = 3380.0      # B定数 [K]
    t25_c: float = 25.0          # 基準温度 [℃]
    r_fixed1: float = 5_000.0    # 分圧の固定抵抗 [Ω]
    r_fixed2: float = 10_000.0    # 分圧の固定抵抗 [Ω]
    vref: float = 2.5            # 基準電圧 [V]


@dataclass
class AdcDacConfig:
    """ADN8834 OUT1 の ADC / OUT2 指令の DAC 設定（ともに16bit）。"""
    bits: int = 16
    vref: float = 2.5            # フルスケール電圧 [V]

    @property
    def max_code(self) -> int:
        return (1 << self.bits) - 1  # 65535


@dataclass
class ThermalConfig:
    """負荷（レーザー実装）側の1次遅れ熱モデル。"""
    heat_capacity: float = 5.0   # 熱容量 C [J/K]
    r_thermal: float = 4.0       # 周囲への熱抵抗 Rth [K/W]（τ = Rth·C ≈ 20s）
    ambient_c: float = 25.0      # 周囲温度 Ta [℃]
    init_c: float = 25.0         # 初期温度 [℃]


@dataclass
class PeltierConfig:
    """ペルチェの線形近似（V_out2 指令 → 冷却パワー）。

    DAC 中央コードを 0（無駆動）とし、正で冷却・負で加熱の双極性駆動とする。
    """
    k_pelt: float = 2.29         # 駆動ゲイン [W/V]（正=冷却）。小信号 (S·Tc)/R
    # S·Tc=(Qc,max+½·Imax²·R)/Imax=(4.3+3.34)/2=3.82W/A, /R(1.67)=2.29
    q_max: float = 4.3           # 冷却/加熱パワーの上限 [W]（OTX20-31 Qc,max @ Thot27℃）
    r_elec: float = 1.67         # ペルチェ電気抵抗 [Ω]（OTX20-31 Module Resistance、負荷線 V=I·R）
    v_rating: float = 3.6        # 定格最大電圧 Vmax [V]（OTX20-31 @ Thot27℃）
    i_rating: float = 2.0        # 定格最大電流 Imax [A]（OTX20-31 @ Thot27℃）


@dataclass
class TecDriverConfig:
    """ADN8834 TEC ドライバのリミット設定と指令電圧クランプ。

    電圧/電流リミットは分圧抵抗で決まる（データシートの式）。
    指令電圧クランプは各方向 0〜1 の割合（1=最大振れ±1.25V）で与える。
    """
    # 電圧リミット分圧（Rv1:VREFへ, Rv2:GNDへ）
    rv1: float = 100_000.0
    rv2: float = 200_000.0
    # 電流リミット分圧（Rc1:VREFへ, Rc2:GNDへ）
    rc1: float = 100_000.0
    rc2: float = 45_000.0
    # 定数（ADN8834 データシート）
    vref: float = 2.5            # 基準電圧 [V]
    vdd: float = 3.3             # 電源電圧 [V]（TEC 電圧の上限）
    a_vlim: float = 2.0          # VLIM→TEC 電圧ゲイン [V/V]
    isink_vlim: float = 10e-6    # VLIM 電流シンク（加熱時）[A]
    isink_ilim: float = 40e-6    # ILIM 電流シンク（冷却時）[A]
    r_cs: float = 0.525          # 電流センスゲイン [V/A]
    i_center: float = 1.25       # 電流センス中心電圧 [V]（=VREF/2）
    derate: float = 0.7          # 安全率（定格×derate を上限とする）
    # 指令電圧クランプ割合（0〜1、方向別）
    cmd_ratio_cool: float = 1.0
    cmd_ratio_heat: float = 1.0


@dataclass
class PidConfig:
    """離散 PID の初期ゲインと出力制限。制御量は ADC コードそのもの。"""
    kp: float = 8.0
    ki: float = 2.0
    kd: float = 0.5
    out_min: float = -32768.0    # PID 出力の下限（DAC 双極性コードに対応）
    out_max: float = 32767.0     # PID 出力の上限
    reverse: bool = False        # 順作用（error=setpoint-measurement）。OUT2↑で冷却減=正ゲインプラント


@dataclass
class SimConfig:
    """シミュレーション全体の設定。"""
    dt: float = 0.04              # 制御周期 [s]
    target_c: float = 25.0       # 目標温度 [℃]
    laser_power: float = 0.0     # 外乱：レーザー発熱 [W]（0〜2W）
    history_seconds: float = 120.0  # グラフ保持時間 [s]

    thermistor: ThermistorConfig = None
    adc: AdcDacConfig = None
    thermal: ThermalConfig = None
    peltier: PeltierConfig = None
    pid: PidConfig = None
    tec: TecDriverConfig = None

    def __post_init__(self):
        # 各サブ設定を既定値で初期化（未指定時）
        self.thermistor = self.thermistor or ThermistorConfig()
        self.adc = self.adc or AdcDacConfig()
        self.thermal = self.thermal or ThermalConfig()
        self.peltier = self.peltier or PeltierConfig()
        self.pid = self.pid or PidConfig()
        self.tec = self.tec or TecDriverConfig()


def default_config() -> SimConfig:
    """既定の代表値でシミュレーション設定を生成する。"""
    return SimConfig()
