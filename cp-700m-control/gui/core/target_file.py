"""
target_file.py
目標位置ライブラリ（JSON）の読み込み／保存。

1つのファイルに最大 30 スロットの目標位置を保持する。各スロットは
番号（1〜30）・名前・移動モード（absolute/relative）・3軸の目標位置 [mm] を持つ。

JSON 形式:
    {
      "targets": {
        "1": {"name": "原点付近", "mode": "absolute",
              "axes": {"1": 10.5, "2": 20.0, "3": 3.25}},
        "2": {"name": "検査位A", "mode": "relative",
              "axes": {"1": 0.0, "2": 5.0, "3": 0.0}}
      }
    }
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.config import AXES

SLOT_COUNT = 30


@dataclass
class TargetSlot:
    """1スロット分の目標位置。"""
    name: str
    mode: str                 # "absolute" | "relative"
    axes: dict[str, float]    # {"1": x, "2": y, "3": z} [mm]


def _normalize_mode(text: str) -> str:
    s = str(text).strip().lower()
    if s in ("absolute", "abs", "絶対"):
        return "absolute"
    if s in ("relative", "rel", "相対"):
        return "relative"
    raise ValueError(f"移動モードは absolute/relative で指定してください: {text!r}")


def load_target_library(path: str | Path) -> dict[int, TargetSlot]:
    """JSON を読み {slot_no: TargetSlot} を返す。ファイル無しは空 dict。壊れていれば ValueError。"""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON として解釈できません: {exc}") from exc
    slots: dict[int, TargetSlot] = {}
    for k, v in (data.get("targets", {}) or {}).items():
        try:
            no = int(k)
        except (TypeError, ValueError):
            continue
        if not (1 <= no <= SLOT_COUNT):
            continue
        try:
            axes = {ax: float(v["axes"][ax]) for ax in AXES}
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"スロット {no} の軸値が不正です: {exc}") from exc
        slots[no] = TargetSlot(str(v.get("name", "")),
                               _normalize_mode(v.get("mode", "absolute")), axes)
    return slots


def save_target_library(path: str | Path, slots: dict[int, TargetSlot]) -> None:
    """{slot_no: TargetSlot} を JSON へ保存する（番号順、UTF-8）。"""
    data = {
        "targets": {
            str(no): {
                "name": s.name,
                "mode": s.mode,
                "axes": {ax: round(float(s.axes[ax]), 3) for ax in AXES},
            }
            for no, s in sorted(slots.items())
        }
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
