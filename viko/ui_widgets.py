# viko/ui_widgets.py
from __future__ import annotations
import math, time
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient, QFontMetrics,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QSizePolicy,
)

from viko.ui_theme import (
    _c, BG, CARD, TXT, DIM, PRI, AMB, SUC, ERR,
    pri, amb, suc, F,
    WIN_W, WIN_H, HDR_H, FTR_H, LEFT_W, RIGHT_W, _WORLD_POLYS,
)


class FloatingArc(QWidget):
    """Centered trapezoidal arch panel floating with dark space on left/right."""

    def __init__(self, draw_fn, height: int, flip: bool = False,
                 on_click=None, state: dict | None = None, parent=None):
        super().__init__(parent)
        self._draw     = draw_fn
        self._flip     = flip
        self._tick     = 0
        self._on_click = on_click
        self._state    = state or {}
        self.setFixedHeight(height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        t = QTimer(self); t.timeout.connect(self._step); t.start(50)

    def _step(self): self._tick += 1; self.update()

    def _panel_btn_rect(self):
        W  = self.width()
        pw = int(W * 0.50)
        px = (W - pw) // 2
        bx = px + pw - 30 - 96
        return bx, bx + 96

    def mousePressEvent(self, e):
        if self._on_click and self._flip:
            x = int(e.position().x())
            x1, x2 = self._panel_btn_rect()
            if x1 <= x <= x2:
                self._on_click()

    def mouseMoveEvent(self, e):
        if self._flip:
            x = int(e.position().x())
            x1, x2 = self._panel_btn_rect()
            self.setCursor(Qt.CursorShape.PointingHandCursor
                           if x1 <= x <= x2 else Qt.CursorShape.ArrowCursor)

    def _path(self) -> QPainterPath:
        W, H = self.width(), self.height()
        pw    = int(W * 0.50)
        px    = (W - pw) // 2
        slant = 30
        pad   = 3
        path = QPainterPath()
        if not self._flip:
            path.moveTo(px,              pad)
            path.lineTo(px + pw,         pad)
            path.lineTo(px + pw - slant, H - pad - 6)
            path.quadTo(W / 2,           H - pad + 10,
                        px + slant,      H - pad - 6)
            path.closeSubpath()
        else:
            path.moveTo(px,           H - pad)
            path.lineTo(px + slant,   pad + 6)
            path.quadTo(W / 2,        pad - 8,
                        px + pw - slant, pad + 6)
            path.lineTo(px + pw,      H - pad)
            path.closeSubpath()
        return path

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        path = self._path()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0, _c(6, 18, 34, 240))
        g.setColorAt(1, _c(3, 10, 20, 250))
        p.fillPath(path, QBrush(g))
        p.setPen(QPen(pri(16), 8)); p.drawPath(path)
        alpha = int(75 + 50 * math.sin(self._tick * 0.09))
        p.setPen(QPen(pri(alpha), 1.3)); p.drawPath(path)
        self._draw(p, W, H, self._tick, self._state)
        p.end()
