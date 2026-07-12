"""ADN8834 TEC ドライバのリミット計算と指令電圧クランプ。

分圧抵抗から電圧/電流リミット（heating/cooling）を算出し、
ペルチェ負荷線 V=I·R と VDD を考慮した実効最大、定格×derate に対する
推奨指令比率、判定を提供する。GUI「TECリミット」タブと Simulator が使う。
"""
from config import TecDriverConfig, PeltierConfig

_GAIN_OUT2 = 5.0  # ADN8834 差動出力段の固定ゲイン（V_TEC = 5·(VREF/2 − OUT2)）


def compute_limits(tec: TecDriverConfig) -> dict:
    """分圧抵抗から ADN8834 の電圧/電流ハードリミットを算出する。"""
    vref = tec.vref
    # --- 電圧リミット ---
    vvlim_cool = vref * tec.rv2 / (tec.rv1 + tec.rv2)
    rv_par = tec.rv1 * tec.rv2 / (tec.rv1 + tec.rv2)
    vvlim_heat = vvlim_cool - tec.isink_vlim * rv_par
    vlim_cool = vvlim_cool * tec.a_vlim
    vlim_heat = vvlim_heat * tec.a_vlim
    # --- 電流リミット ---
    vilim_heat = vref * tec.rc2 / (tec.rc1 + tec.rc2)
    rc_par = tec.rc1 * tec.rc2 / (tec.rc1 + tec.rc2)
    vilim_cool = vilim_heat + tec.isink_ilim * rc_par
    ilim_cool = (vilim_cool - tec.i_center) / tec.r_cs
    ilim_heat = (tec.i_center - vilim_heat) / tec.r_cs
    return dict(vlim_cool=vlim_cool, vlim_heat=vlim_heat,
                ilim_cool=ilim_cool, ilim_heat=ilim_heat)


def _effective(vlim: float, ilim: float, r_elec: float, vdd: float):
    """負荷線 V=I·R と VDD を考慮した実効最大 TEC 電圧と律速要因を返す。"""
    candidates = {"Vlim": vlim, "Ilim": ilim * r_elec, "VDD": vdd}
    binding = min(candidates, key=candidates.get)
    return candidates[binding], binding


def effective_max(tec: TecDriverConfig, pelt: PeltierConfig) -> dict:
    """各方向の実効最大 TEC 電圧/電流（律速要因つき）を返す。"""
    lim = compute_limits(tec)
    r = pelt.r_elec
    veff_cool, bind_cool = _effective(lim["vlim_cool"], lim["ilim_cool"], r, tec.vdd)
    veff_heat, bind_heat = _effective(lim["vlim_heat"], lim["ilim_heat"], r, tec.vdd)
    out = dict(lim)
    out.update(veff_cool=veff_cool, ieff_cool=veff_cool / r, bind_cool=bind_cool,
               veff_heat=veff_heat, ieff_heat=veff_heat / r, bind_heat=bind_heat)
    return out


def _rec_ratio(veff: float, center: float, vsafe: float, isafe: float,
               r_elec: float) -> float:
    """定格×derate に収まる最大の指令比率（0〜1）。

    指令比率 ratio では OUT2 の振れ = ratio·center、要求 V_TEC = 5·center·ratio
    （実効最大 veff で飽和）。安全上限 vtec_safe=min(vsafe, isafe·R) を超えない ratio。
    """
    vtec_safe = min(vsafe, isafe * r_elec)
    if veff <= vtec_safe + 1e-9:
        return 1.0  # 実効最大まで振り切っても安全
    denom = _GAIN_OUT2 * center
    if denom <= 0:
        return 1.0
    return max(0.0, min(1.0, vtec_safe / denom))


def recommended_ratios(tec: TecDriverConfig, pelt: PeltierConfig):
    """定格×derate に収まる推奨指令比率 (cool, heat) を返す。"""
    eff = effective_max(tec, pelt)
    center = tec.vref / 2.0
    vsafe = pelt.v_rating * tec.derate
    isafe = pelt.i_rating * tec.derate
    r_cool = _rec_ratio(eff["veff_cool"], center, vsafe, isafe, pelt.r_elec)
    r_heat = _rec_ratio(eff["veff_heat"], center, vsafe, isafe, pelt.r_elec)
    return r_cool, r_heat


def evaluate(tec: TecDriverConfig, pelt: PeltierConfig) -> dict:
    """判定表に必要な全情報（各方向の実効最大・指令点・合否・推奨比率）を返す。"""
    eff = effective_max(tec, pelt)
    vsafe = pelt.v_rating * tec.derate
    isafe = pelt.i_rating * tec.derate
    rec_cool, rec_heat = recommended_ratios(tec, pelt)
    center = tec.vref / 2.0  # 指令電圧の中点（無駆動）[V]
    r = pelt.r_elec

    def row(name, vlim, ilim, veff, ieff, bind, ratio, rec, sign):
        # 指令電圧(OUT2, 絶対値 0〜VREF)：冷却=中点から下げ, 加熱=中点から上げ。
        # 比率1 で 冷却→0V, 加熱→VREF(2.5V)。
        vcmd = center + sign * ratio * center
        # OUT2 振れ ratio·center → 要求 V_TEC = 5·center·ratio（実効最大で飽和）
        v = min(_GAIN_OUT2 * center * ratio, veff)
        i = v / r if r > 0 else 0.0
        return dict(
            name=name, vlim=vlim, ilim=ilim, veff=veff, ieff=ieff, binding=bind,
            ratio=ratio, vcmd=vcmd, v_tec=v, i_tec=i,
            v_ok=(v <= vsafe + 1e-9), i_ok=(i <= isafe + 1e-9), rec=rec,
        )

    cool = row("冷却", eff["vlim_cool"], eff["ilim_cool"], eff["veff_cool"],
               eff["ieff_cool"], eff["bind_cool"], tec.cmd_ratio_cool, rec_cool, -1.0)
    heat = row("加熱", eff["vlim_heat"], eff["ilim_heat"], eff["veff_heat"],
               eff["ieff_heat"], eff["bind_heat"], tec.cmd_ratio_heat, rec_heat, +1.0)
    return dict(vsafe=vsafe, isafe=isafe, vcmd_center=center, vref=tec.vref,
                cool=cool, heat=heat)
