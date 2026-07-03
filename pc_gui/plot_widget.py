"""Rolling time-series plot (pyqtgraph), promotable in Qt Designer.

In Designer, drop a QWidget placeholder and *promote* it to:
    class name : RollingPlot
    header     : plot_widget
The controller then calls configure() after the UI is loaded.
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer


class RollingPlot(pg.PlotWidget):
    """Live scrolling plot of a value vs. time [s].

    Promotable: the constructor only takes `parent` (Qt Designer requirement).
    Appearance/axis are set later via configure(). Samples are pushed with
    add(t, value); the curve is redrawn on a fixed timer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window_s = 30.0
        self._t: deque[float] = deque()
        self._v: deque[float] = deque()
        self._dirty = False

        self.setBackground("w")
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel("bottom", "Time", units="s")
        self._curve = self.plot(pen=pg.mkPen("#1565c0", width=1),
                                symbol="o", symbolSize=5, symbolBrush="b")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._redraw)
        self._timer.start(33)   # ~30 FPS

    def configure(self, ylabel="Value", yunits="", yrange=None,
                  color="#1565c0", window_s: float = 30.0) -> None:
        self._window_s = window_s
        self.setLabel("left", ylabel, units=yunits)
        if yrange is not None:
            self.setYRange(*yrange)
        else:
            self.enableAutoRange(axis="y")
        self._curve.setPen(pg.mkPen(color, width=1))
        self._curve.setSymbolBrush(color)

    def add(self, t: float, value: float) -> None:
        """Append a sample at explicit time t [s] (derived from the sample seq
        so spacing is exact, independent of host receive jitter)."""
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
