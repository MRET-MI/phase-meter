"""CP-700M 自動ステージ制御（phase-meter GUI 用にコピー）。

元は `cp-700m-control/gui/` の core/comm 一式。プロジェクト自己完結のため複製し、
import をパッケージ相対に調整している。
"""

from .controller import Cp700Controller, StageStatus, parse_status
from .transport import SerialTransport, MockTransport, TransportError
from .config import AxisConfig, Cp700Config
from . import commands

__all__ = [
    "Cp700Controller", "StageStatus", "parse_status",
    "SerialTransport", "MockTransport", "TransportError",
    "AxisConfig", "Cp700Config", "commands",
]
