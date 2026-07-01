"""Rolling time-series plot (pyqtgraph), used for phase and amplitude."""

from __future__ import annotations

import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer


class RollingPlot(pg.PlotWidget):
    """Live scrolling plot of a value vs. time [s].

    Samples are pushed via add(); the curve is redrawn on a fixed timer
    (decoupled from the ~100 Hz arrival rate to keep the UI smooth).

    yrange=None enables auto-ranging on the Y axis.
    """

    def __init__(self, ylabel="Phase difference", yunits="deg",
                 yrange=(-180, 180), color="#1565c0",
                 window_s: float = 30.0, redraw_hz: float = 30.0, parent=None):
        super().__init__(parent)
        self._window_s = window_s
        self._t0 = time.monotonic()
        self._t: deque[float] = deque()
        self._v: deque[float] = deque()
        self._dirty = False

        self.setBackground("w")
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel("left", ylabel, units=yunits)
        self.setLabel("bottom", "Time", units="s")
        if yrange is not None:
            self.setYRange(*yrange)
        else:
            self.enableAutoRange(axis="y")
        self._curve = self.plot(pen=pg.mkPen(color, width=2))

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._redraw)
        self._timer.start(int(1000 / redraw_hz))

    def add(self, value: float) -> None:
        t = time.monotonic() - self._t0
        self._t.append(t)
        self._v.append(value)
        cutoff = t - self._window_s
        while self._t and self._t[0] < cutoff:
            self._t.popleft()
            self._v.popleft()
        self._dirty = True

    def clear_data(self) -> None:
        self._t.clear()
        self._v.clear()
        self._dirty = True

    def _redraw(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        if self._t:
            self._curve.setData(np.fromiter(self._t, float), np.fromiter(self._v, float))
        else:
            self._curve.clear()
