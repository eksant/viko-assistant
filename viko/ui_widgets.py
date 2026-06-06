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


def _hdr_draw(p: QPainter, W: int, H: int, tick: int, state: dict = {}):
    pw    = int(W * 0.50)
    px    = (W - pw) // 2
    slant = 30
    x1    = px + slant + 10
    x2    = px + pw - slant - 10
    cx    = W // 2

    p.setFont(F(8, True)); p.setPen(pri(100))
    p.drawText(x1, H // 2 - 1, "B.1.0.0")
    p.setFont(F(7)); p.setPen(pri(55))
    p.drawText(x1, H // 2 + 15, "VIKO ASSISTANT")

    p.setFont(F(18, True)); p.setPen(PRI)
    fm = QFontMetrics(p.font())
    titl = "VIKO"
    p.drawText(cx - fm.horizontalAdvance(titl) // 2, H // 2 + 7, titl)

    p.setFont(F(8)); p.setPen(pri(70))
    sub = "JUST A RATHER VERY INTELLIGENT SYSTEM"
    fm2 = QFontMetrics(p.font())
    p.drawText(cx - fm2.horizontalAdvance(sub) // 2, H // 2 + 21, sub)

    p.setFont(F(12, True)); p.setPen(AMB)
    clk = time.strftime("%H:%M:%S")
    fm3 = QFontMetrics(p.font())
    p.drawText(x2 - fm3.horizontalAdvance(clk), H // 2 + 7, clk)

    p.setFont(F(7)); p.setPen(DIM)
    dat = time.strftime("%a  %d %b %Y")
    fm4 = QFontMetrics(p.font())
    p.drawText(x2 - fm4.horizontalAdvance(dat), H // 2 + 21, dat)


def _ftr_draw(p: QPainter, W: int, H: int, tick: int, state: dict = {}):
    pw    = int(W * 0.50)
    px    = (W - pw) // 2
    slant = 30
    x1    = px + slant + 10
    x2    = px + pw - slant - 10
    cx    = W // 2
    cy    = H // 2 + 6

    p.setFont(F(7)); p.setPen(pri(100))
    p.drawText(x1, cy - 3, "[F4] Mute  ·  [F11] Fullscreen")

    ma = int(150 + 105 * abs(math.sin(tick * 0.14)))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(suc(ma)))
    p.drawEllipse(QPointF(x1 + 2, cy + 11), 3.5, 3.5)
    p.setFont(F(7)); p.setPen(suc(160))
    p.drawText(x1 + 10, cy + 16, "MIC ACTIVE")

    p.setFont(F(8, True)); p.setPen(pri(90))
    brand = "VIKO  ·  B.1.0.0  ·  CLASSIFIED"
    fm = QFontMetrics(p.font())
    p.drawText(cx - fm.horizontalAdvance(brand) // 2, cy + 7, brand)

    p.setFont(F(7)); p.setPen(pri(65))
    copy = "© VIKO INDUSTRIES"
    fm2 = QFontMetrics(p.font())
    p.drawText(x2 - fm2.horizontalAdvance(copy), cy + 7, copy)


class MetricCard(QWidget):
    def __init__(self, label: str, val_fn, color=None, parent=None):
        super().__init__(parent)
        self._label  = label
        self._val_fn = val_fn   # () -> (float 0..1, str)
        self._col    = color or PRI
        self._tick   = 0
        self.setFixedHeight(78)
        t = QTimer(self); t.timeout.connect(self._step); t.start(60)

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        val, text = self._val_fn()
        p.setPen(QPen(_c(0, 212, 255, 28), 1))
        p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 7, 7)

        r = 23; acx = 36; acy = H // 2
        rect = QRectF(acx - r, acy - r, r * 2, r * 2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(pri(26), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int(210 * 16), int(-240 * 16))
        cg = QConicalGradient(QPointF(acx, acy), 150)
        cg.setColorAt(0, self._col); cg.setColorAt(1, _c(0, 212, 255, 55))
        p.setPen(QPen(QBrush(cg), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int(210 * 16), int(-240 * val * 16))

        p.setFont(F(9, True)); p.setPen(self._col)
        fm = QFontMetrics(p.font())
        p.drawText(acx - fm.horizontalAdvance(text) // 2, acy + 5, text)

        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(acx + r + 10, acy - 10, self._label)

        bx = acx + r + 10; by = acy + 4; bw = W - bx - 10; bh = 4
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(pri(20)))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)
        lg = QLinearGradient(bx, 0, bx + bw, 0)
        lg.setColorAt(0, pri(135)); lg.setColorAt(1, self._col)
        p.setBrush(QBrush(lg))
        p.drawRoundedRect(QRectF(bx, by, bw * val, bh), 2, 2)
        p.end()


class SystemStatusCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self._online = True   # set via set_online(bool)
        self.setFixedHeight(56)
        t = QTimer(self); t.timeout.connect(self._step); t.start(60)

    def set_online(self, online: bool):
        self._online = online; self.update()

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        p.setPen(QPen(pri(28), 1))
        p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 7, 7)

        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 16, "SYSTEM STATUS")

        col_fn = suc if self._online else (lambda a=255: _c(255, 68, 68, a))
        lbl_txt = "ONLINE" if self._online else "OFFLINE"

        da = int(210 + 45 * math.sin(self._tick * 0.10))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(col_fn(da)))
        p.drawEllipse(QRectF(10, 23, 10, 10))
        pr_r = 7 + 3 * math.sin(self._tick * 0.10)
        pa   = int(80 + 60 * abs(math.sin(self._tick * 0.10)))
        p.setPen(QPen(col_fn(pa), 0.8)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(15, 28), pr_r, pr_r)

        p.setFont(F(11, True)); p.setPen(col_fn())
        p.drawText(27, 35, lbl_txt)

        p.setFont(F(7)); p.setPen(pri(110))
        p.drawText(10, H - 8, "B.1.0.0")
        p.setFont(F(7)); p.setPen(pri(65))
        p.drawText(W // 2, H - 8, "GEMINI API")
        p.end()


class WorldMapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self.setFixedHeight(116)
        t = QTimer(self); t.timeout.connect(self._step); t.start(50)

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        lbl_h = 13; mx = 2; my = lbl_h; mh = H - my - 10

        def proj(lon, lat):
            x = mx + (lon + 180) / 360 * (W - 2 * mx)
            y = my + (90 - lat) / 180 * mh
            return QPointF(x, y)

        p.setPen(QPen(pri(10), 0.5))
        for lon in range(-180, 181, 45):
            p.drawLine(proj(lon, 90), proj(lon, -90))
        for lat in range(-60, 61, 30):
            p.drawLine(proj(-180, lat), proj(180, lat))
        p.setPen(QPen(pri(20), 0.6, Qt.PenStyle.DashLine))
        p.drawLine(proj(-180, 0), proj(180, 0))

        for poly in _WORLD_POLYS:
            path = QPainterPath()
            for i, (lon, lat) in enumerate(poly):
                pt = proj(lon, lat)
                if i == 0: path.moveTo(pt)
                else:       path.lineTo(pt)
            path.closeSubpath()
            p.setBrush(QBrush(pri(12))); p.setPen(QPen(pri(65), 0.7))
            p.drawPath(path)

        kl = proj(101.69, 3.14)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(AMB))
        p.drawEllipse(kl, 3.2, 3.2)
        pr_r = 5.5 + 3.5 * math.sin(self._tick * 0.13)
        pa   = int(160 + 80 * math.sin(self._tick * 0.13))
        p.setPen(QPen(amb(pa // 2), 0.9)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(kl, pr_r, pr_r)

        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(0, 11, "LOCATION  TRACKING")
        p.setFont(F(7)); p.setPen(amb(175))
        p.drawText(0, H, "03°08′N  101°42′E")
        p.end()


class CommsCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self._latency_ms = 180   # updated via set_latency(ms)
        self.setFixedHeight(72)
        t = QTimer(self); t.timeout.connect(self._step); t.start(60)

    def set_latency(self, ms: int): self._latency_ms = ms; self.update()

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        p.setPen(QPen(pri(28), 1)); p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 7, 7)

        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 16, "COMMS  ·  GEMINI API")

        da = int(210 + 45 * math.sin(self._tick * 0.10))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(suc(da)))
        p.drawEllipse(QRectF(10, 24, 8, 8))
        p.setFont(F(11, True)); p.setPen(SUC)
        p.drawText(24, 35, "ONLINE")

        lat = min(1.0, self._latency_ms / 1000)
        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 54, "LATENCY")
        bx, by, bw, bh = 58, 46, W - 68, 5
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(pri(20)))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)
        lg = QLinearGradient(bx, 0, bx + bw, 0)
        lg.setColorAt(0, suc(175)); lg.setColorAt(1, pri(115))
        p.setBrush(QBrush(lg))
        p.drawRoundedRect(QRectF(bx, by, bw * lat, bh), 2, 2)
        p.setFont(F(7)); p.setPen(suc(175))
        p.drawText(int(bx + bw * lat) + 4, 54, f"{self._latency_ms}ms")
        p.end()


class SessionCard(QWidget):
    _t0 = time.time()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self._ops  = 0   # updated via inc_ops()
        self.setFixedHeight(60)
        t = QTimer(self); t.timeout.connect(self._step); t.start(1000)

    def inc_ops(self): self._ops += 1; self.update()

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        p.setPen(QPen(pri(28), 1)); p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 7, 7)

        e = int(time.time() - self._t0)
        ts = f"{e // 3600:02d}:{(e % 3600) // 60:02d}:{e % 60:02d}"

        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 16, "SESSION INTEL")
        p.setFont(F(12, True)); p.setPen(AMB)
        p.drawText(10, 38, ts)
        p.setFont(F(7)); p.setPen(pri(135))
        p.drawText(10, 53, "UPTIME")
        p.drawText(W // 2, 53, f"OPS: {self._ops}")
        p.end()
