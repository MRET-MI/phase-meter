"""Rolling time-series plot (pyqtgraph), promotable in Qt Designer.

In Designer, drop a QWidget placeholder and *promote* it to:
    class name : RollingPlot
    header     : plot_widget
The controller then calls configure() (single series) or configure_multi()
(several overlaid series) after the UI is loaded.
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer


class RollingPlot(pg.PlotWidget):
    """Live scrolling plot of one or more values vs. time [s].

    Promotable: the constructor only takes `parent` (Qt Designer requirement).
    Appearance/axis are set later via configure() (1 series, backward
    compatible) or configure_multi() (N overlaid series with a legend).
    Samples are pushed with add(t, value) / add_curve(idx, t, value); the
    curves are redrawn on a fixed timer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window_s = 30.0
        self._dirty = False
        self._curves: list = []
        self._data: list[tuple[deque, deque]] = []   # per series: (t, v)
        self._legend = None

        self.setBackground("w")
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel("bottom", "Time", units="s")

        # Default single series (with markers) — preserves the old behaviour.
        self._add_series("#1565c0", symbol=True)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._redraw)
        self._timer.start(33)   # ~30 FPS

    # ── series management ──────────────────────────────────────────────────
    def _add_series(self, color: str, symbol: bool = False, name=None):
        if symbol:
            curve = self.plot(pen=pg.mkPen(color, width=1),
                              symbol="o", symbolSize=5, symbolBrush=color, name=name)
        else:
            curve = self.plot(pen=pg.mkPen(color, width=1), name=name)
        self._curves.append(curve)
        self._data.append((deque(), deque()))
        return curve

    def _reset_series(self) -> None:
        for c in self._curves:
            self.removeItem(c)
        self._curves.clear()
        self._data.clear()

    # ── configuration ──────────────────────────────────────────────────────
    def configure(self, ylabel="Value", yunits="", yrange=None,
                  color="#1565c0", window_s: float = 30.0) -> None:
        """Single-series configuration (backward compatible)."""
        self._window_s = window_s
        self.setLabel("left", ylabel, units=yunits)
        if yrange is not None:
            self.setYRange(*yrange)
        else:
            self.enableAutoRange(axis="y")
        if not self._curves:
            self._add_series(color, symbol=True)
        self._curves[0].setPen(pg.mkPen(color, width=1))
        try:
            self._curves[0].setSymbolBrush(color)
        except Exception:
            pass

    def configure_multi(self, series, ylabel="", yunits="", yrange=None,
                        window_s: float = 30.0, legend: bool = True) -> None:
        """Configure N overlaid series. `series` = [(label, color), ...]."""
        self._window_s = window_s
        self._reset_series()
        if legend:
            self._legend = self.addLegend()
        for label, color in series:
            self._add_series(color, symbol=False, name=label)
        self.setLabel("left", ylabel, units=yunits)
        if yrange is not None:
            self.setYRange(*yrange)
        else:
            self.enableAutoRange(axis="y")

    # ── data ───────────────────────────────────────────────────────────────
    def add(self, t: float, value: float) -> None:
        """Append a sample to series 0 (backward compatible)."""
        self.add_curve(0, t, value)

    def add_curve(self, idx: int, t: float, value: float) -> None:
        """Append a sample at explicit time t [s] to series `idx` (t is derived
        from the sample seq/tick so spacing is exact, jitter-free)."""
        if idx < 0 or idx >= len(self._data):
            return
        tq, vq = self._data[idx]
        tq.append(t)
        vq.append(value)
        cutoff = t - self._window_s
        while tq and tq[0] < cutoff:
            tq.popleft()
            vq.popleft()
        self._dirty = True

    def clear_data(self) -> None:
        for tq, vq in self._data:
            tq.clear()
            vq.clear()
        self._dirty = True

    def _redraw(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        for curve, (tq, vq) in zip(self._curves, self._data):
            if tq:
                curve.setData(np.fromiter(tq, float), np.fromiter(vq, float))
            else:
                curve.clear()
