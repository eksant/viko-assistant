#!/usr/bin/env python3
"""
VIKO – JARVIS Modern HUD  |  Design Preview v1
Run: python design_preview.py
"""
from __future__ import annotations
import math, sys, time

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush,
    QFont, QLinearGradient, QRadialGradient, QConicalGradient,
    QFontMetrics,
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QTextEdit, QLabel, QLineEdit, QPushButton, QStackedWidget,
)

WIN_W, WIN_H = 1160, 740
HDR_H  = 62
FTR_H  = 58
LEFT_W = 224
RIGHT_W = 288


# ── palette ───────────────────────────────────────────────────────────────────
def _c(r, g, b, a=255): return QColor(r, g, b, a)

BG   = _c(0,   0,  0)
CARD = _c(4,   8, 14)
TXT  = _c(200, 232, 248)
DIM  = _c(42,  74, 106)
PRI  = _c(0,  212, 255)
AMB  = _c(255, 179, 71)
SUC  = _c(0,  255, 159)
ERR  = _c(255, 68,  68)

def pri(a=255): return _c(0,   212, 255, a)
def amb(a=255): return _c(255, 179, 71,  a)
def suc(a=255): return _c(0,   255, 159, a)

def F(sz: int, bold: bool = False) -> QFont:
    f = QFont("Courier New", sz)
    f.setBold(bold)
    return f


# Simplified continent outlines as (lon, lat) polygons
_WORLD_POLYS = [
    # North America
    [(-168,71),(-140,70),(-125,60),(-124,49),(-117,32),(-90,20),
     (-80,8),(-65,11),(-55,47),(-65,44),(-75,38),(-85,30),
     (-97,20),(-110,32),(-120,40),(-124,48),(-148,61),(-165,64),(-168,71)],
    # Greenland
    [(-73,76),(-50,76),(-20,68),(-25,60),(-43,60),(-55,64),(-73,76)],
    # South America
    [(-73,12),(-55,5),(-38,-4),(-35,-35),(-52,-55),(-68,-55),
     (-76,-45),(-72,-35),(-70,-18),(-80,-2),(-73,12)],
    # Europe
    [(-10,36),(-5,48),(0,51),(5,53),(10,57),(20,60),(28,70),
     (28,66),(20,60),(25,55),(18,48),(15,45),(14,41),(8,44),
     (5,43),(-2,43),(-10,36)],
    # Africa
    [(-17,15),(-17,21),(-5,36),(10,37),(12,33),(25,30),(32,31),
     (37,18),(43,12),(50,12),(42,0),(40,-8),(36,-25),(26,-34),
     (19,-35),(14,-23),(12,-5),(10,4),(0,5),(-10,5),(-13,8),(-17,15)],
    # Asia (main + Middle East + India + Indochina merged)
    [(34,29),(36,38),(40,41),(50,41),(60,38),(75,38),(85,36),
     (100,55),(120,50),(135,48),(140,46),(145,45),(155,52),(168,68),
     (140,38),(135,35),(130,34),(122,32),(115,22),(110,20),(105,13),
     (104,1),(100,3),(100,15),(90,23),(85,28),(80,30),(72,22),(65,20),
     (60,24),(55,24),(48,18),(43,12),(37,18),(32,31),(34,29)],
    # Australia
    [(114,-22),(118,-30),(124,-35),(130,-34),(138,-35),(140,-38),
     (148,-38),(152,-28),(152,-22),(148,-20),(143,-15),(136,-12),
     (130,-13),(122,-17),(116,-20),(114,-22)],
]


# ══════════════════════════════════════════════════════════════════════════════
# FloatingArc — floating ╱‾‾‾╲ arch panel (header / footer)
# ══════════════════════════════════════════════════════════════════════════════
class FloatingArc(QWidget):
    """Centered trapezoidal arch panel that floats with dark space on left/right."""

    def __init__(self, draw_fn, height: int, flip: bool = False,
                 on_click=None, state: dict | None = None, parent=None):
        super().__init__(parent)
        self._draw     = draw_fn
        self._flip     = flip
        self._tick     = 0
        self._on_click = on_click   # callable triggered when PANEL btn clicked
        self._state    = state or {}
        self.setFixedHeight(height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(50)

    def _step(self): self._tick += 1; self.update()

    def _panel_btn_rect(self):
        """Returns (x1, x2) range of the PANEL button in footer."""
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
        pw    = int(W * 0.50)          # panel width = 50% of window
        px    = (W - pw) // 2          # left edge
        slant = 30                     # side angle offset
        pad   = 3

        path = QPainterPath()
        if not self._flip:
            # HEADER: flip vertikal — wide di atas, narrow di bawah, curve ke bawah
            path.moveTo(px,              pad)             # top-left (wide)
            path.lineTo(px + pw,         pad)             # top-right (wide)
            path.lineTo(px + pw - slant, H - pad - 6)    # bottom-right (narrow)
            path.quadTo(W / 2,           H - pad + 10,   # cembung ke bawah
                        px + slant,      H - pad - 6)    # bottom-left (narrow)
            path.closeSubpath()
        else:
            # FOOTER: same ╱‾‾‾╲ shape, bump at top center
            path.moveTo(px,           H - pad)           # bottom-left
            path.lineTo(px + slant,   pad + 6)           # top-left
            path.quadTo(W / 2,        pad - 8,
                        px + pw - slant, pad + 6)        # top-right
            path.lineTo(px + pw,      H - pad)           # bottom-right
            path.closeSubpath()
        return path

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        path = self._path()

        # Fill
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0, _c(6,  18, 34, 240))
        g.setColorAt(1, _c(3,  10, 20, 250))
        p.fillPath(path, QBrush(g))

        # Outer glow
        p.setPen(QPen(pri(16), 8))
        p.drawPath(path)
        # Border (animated breath)
        alpha = int(75 + 50 * math.sin(self._tick * 0.09))
        p.setPen(QPen(pri(alpha), 1.3))
        p.drawPath(path)

        self._draw(p, W, H, self._tick, self._state)
        p.end()


def _hdr_draw(p: QPainter, W: int, H: int, tick: int, state: dict = {}):
    pw    = int(W * 0.50)
    px    = (W - pw) // 2
    slant = 30
    x1    = px + slant + 10       # inner-left
    x2    = px + pw - slant - 10  # inner-right
    cx    = W // 2

    # ── LEFT: version label only ──────────────────────────────────────────
    p.setFont(F(8, True)); p.setPen(pri(100))
    p.drawText(x1, H // 2 - 1, "B.1.0.0")
    p.setFont(F(7)); p.setPen(pri(55))
    p.drawText(x1, H // 2 + 15, "VIKO ASSISTANT")

    # ── CENTER: VIKO title + subtitle ─────────────────────────────────────
    p.setFont(F(18, True)); p.setPen(PRI)
    fm   = QFontMetrics(p.font())
    titl = "VIKO"
    p.drawText(cx - fm.horizontalAdvance(titl) // 2, H // 2 + 7, titl)

    p.setFont(F(8)); p.setPen(pri(70))
    sub = "JUST A RATHER VERY INTELLIGENT SYSTEM"
    fm2 = QFontMetrics(p.font())
    p.drawText(cx - fm2.horizontalAdvance(sub) // 2, H // 2 + 21, sub)

    # ── RIGHT: clock + date ───────────────────────────────────────────────
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

    # ── LEFT: keyboard hints + mic status ─────────────────────────────────
    p.setFont(F(7)); p.setPen(pri(100))
    p.drawText(x1, cy - 3, "[F4] Mute  ·  [F11] Fullscreen")

    ma = int(150 + 105 * abs(math.sin(tick * 0.14)))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(suc(ma)))
    p.drawEllipse(QPointF(x1 + 2, cy + 11), 3.5, 3.5)
    p.setFont(F(7)); p.setPen(suc(160))
    p.drawText(x1 + 10, cy + 16, "MIC ACTIVE")

    # ── CENTER: branding ──────────────────────────────────────────────────
    p.setFont(F(8, True)); p.setPen(pri(90))
    brand = "VIKO  ·  B.1.0.0  ·  CLASSIFIED"
    fm = QFontMetrics(p.font())
    p.drawText(cx - fm.horizontalAdvance(brand) // 2, cy + 7, brand)

    # ── RIGHT: copyright ──────────────────────────────────────────────────
    p.setFont(F(7)); p.setPen(pri(65))
    copy = "© VIKO INDUSTRIES"
    fm2 = QFontMetrics(p.font())
    p.drawText(x2 - fm2.horizontalAdvance(copy), cy + 7, copy)


# ══════════════════════════════════════════════════════════════════════════════
# MetricCard — frosted glass card with radial arc gauge
# ══════════════════════════════════════════════════════════════════════════════
class MetricCard(QWidget):
    def __init__(self, label: str, val_fn, color=None, parent=None):
        super().__init__(parent)
        self._label  = label
        self._val_fn = val_fn      # () -> (float 0..1, str)
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

        # Card bg (frosted glass effect)
        p.setPen(QPen(_c(0, 212, 255, 28), 1))
        p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 7, 7)

        # Radial arc gauge
        r    = 23
        acx  = 36; acy = H // 2
        rect = QRectF(acx - r, acy - r, r*2, r*2)

        # Track arc
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(pri(26), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int(210*16), int(-240*16))

        # Value arc (conical gradient)
        cg = QConicalGradient(QPointF(acx, acy), 150)
        cg.setColorAt(0, self._col)
        cg.setColorAt(1, _c(0, 212, 255, 55))
        p.setPen(QPen(QBrush(cg), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int(210*16), int(-240 * val * 16))

        # Center value text
        p.setFont(F(9, True)); p.setPen(self._col)
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(text)
        p.drawText(acx - tw//2, acy + 5, text)

        # Label
        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(acx + r + 10, acy - 10, self._label)

        # Progress bar
        bx = acx + r + 10; by = acy + 4
        bw = W - bx - 10; bh = 4
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(pri(20)))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)
        lg = QLinearGradient(bx, 0, bx + bw, 0)
        lg.setColorAt(0, pri(135)); lg.setColorAt(1, self._col)
        p.setBrush(QBrush(lg))
        p.drawRoundedRect(QRectF(bx, by, bw * val, bh), 2, 2)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# GlobeCard — 2D wireframe globe with location marker
# ══════════════════════════════════════════════════════════════════════════════
class GlobeCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self.setFixedHeight(134)
        t = QTimer(self); t.timeout.connect(self._step); t.start(50)

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Card bg
        p.setPen(QPen(pri(28), 1))
        p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W-4, H-4), 7, 7)

        r  = 46
        cx = W // 2
        cy = H // 2 + 8

        # Outer glow
        p.setPen(QPen(pri(16), 8)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(pri(55), 1))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Latitude lines
        for lat in [-0.65, -0.35, 0, 0.35, 0.65]:
            ry = r * math.sqrt(max(0, 1 - lat*lat))
            if ry < 3: continue
            p.setPen(QPen(pri(22), 0.8))
            p.drawEllipse(QPointF(cx, cy + lat*r), ry, ry * 0.26)

        # Longitude lines (slowly rotating)
        rot = self._tick * 0.36
        for lng in range(0, 180, 36):
            a_rad = math.radians(lng + rot)
            ex = r * abs(math.cos(a_rad))
            p.setPen(QPen(pri(18), 0.8))
            p.drawEllipse(QPointF(cx, cy), ex, r)

        # Location dot (Kuala Lumpur approx)
        lx = cx + 22; ly = cy - 4
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(AMB))
        p.drawEllipse(QPointF(lx, ly), 4, 4)
        # Pulse ring
        pr_r = 6.5 + 4.5 * math.sin(self._tick * 0.13)
        pa   = int(190 + 65 * math.sin(self._tick * 0.13))
        p.setPen(QPen(amb(pa // 2), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(lx, ly), pr_r, pr_r)

        # Labels
        p.setFont(F(5)); p.setPen(DIM)
        p.drawText(8, 16, "LOCATION  TRACKING")
        p.setFont(F(5)); p.setPen(amb(175))
        p.drawText(8, H - 7, "03°08′N  101°42′E")

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# CommsCard — Gemini API connection status
# ══════════════════════════════════════════════════════════════════════════════
class CommsCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self.setFixedHeight(72)
        t = QTimer(self); t.timeout.connect(self._step); t.start(60)

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setPen(QPen(pri(28), 1))
        p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W-4, H-4), 7, 7)

        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 16, "COMMS  ·  GEMINI API")

        # Online indicator
        da = int(210 + 45 * math.sin(self._tick * 0.10))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(suc(da)))
        p.drawEllipse(QRectF(10, 24, 8, 8))
        p.setFont(F(11, True)); p.setPen(SUC)
        p.drawText(24, 35, "ONLINE")

        # Latency bar
        lat = 0.28 + 0.12 * abs(math.sin(self._tick * 0.06))
        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 54, "LATENCY")
        bx, by, bw, bh = 58, 46, W - 68, 5
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(pri(20)))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)
        lg = QLinearGradient(bx, 0, bx+bw, 0)
        lg.setColorAt(0, suc(175)); lg.setColorAt(1, pri(115))
        p.setBrush(QBrush(lg))
        p.drawRoundedRect(QRectF(bx, by, bw*lat, bh), 2, 2)
        p.setFont(F(7)); p.setPen(suc(175))
        p.drawText(int(bx + bw*lat) + 4, 54, f"{int(lat*600)}ms")

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# SessionCard — session uptime
# ══════════════════════════════════════════════════════════════════════════════
class SessionCard(QWidget):
    _t0 = time.time()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self.setFixedHeight(60)
        t = QTimer(self); t.timeout.connect(self._step); t.start(1000)

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setPen(QPen(pri(28), 1))
        p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W-4, H-4), 7, 7)

        e = int(time.time() - self._t0)
        ts = f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"

        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 16, "SESSION INTEL")

        p.setFont(F(12, True)); p.setPen(AMB)
        p.drawText(10, 38, ts)

        p.setFont(F(7)); p.setPen(pri(135))
        p.drawText(10, 53, "UPTIME")
        p.drawText(W//2, 53, "OPS: 8")

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# HudCanvas — concentric segmented rings + inner orb
# ══════════════════════════════════════════════════════════════════════════════
class HudCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick   = 0
        self._audio  = 0.0
        self._rot    = [0.0] * 7
        self._spd    = [0.28, -0.44, 0.20, -0.36, 0.52, -0.22, 0.12]
        self._pulses: list[float] = [0.0, 80.0, 160.0]
        self._scan     = [0.0, 180.0, 90.0, 270.0]
        self._scan_spd = [1.4, -0.9, 2.1, -1.6]
        # listening / speaking state
        self.state        = "idle"     # "idle" | "listening" | "speaking"
        self._blink       = True
        self._blink_tick  = 0
        self._cycle_tick  = 0
        N = 48
        self._wave        = [0.0] * N  # waveform bar heights (0..1)
        self.setMinimumSize(320, 320)
        t = QTimer(self); t.timeout.connect(self._step); t.start(40)

    def _step(self):
        self._tick += 1
        self._audio = 0.30 + 0.28 * abs(math.sin(self._tick * 0.07))
        for i in range(7):
            self._rot[i] = (self._rot[i] + self._spd[i]) % 360

        # expand pulses, spawn new one periodically
        lim = 210.0
        spd = 1.8 + self._audio * 0.8
        self._pulses = [r + spd for r in self._pulses if r + spd < lim]
        if len(self._pulses) < 4 and self._tick % 38 == 0:
            self._pulses.append(0.0)

        # advance scanners
        for i in range(4):
            self._scan[i] = (self._scan[i] + self._scan_spd[i]) % 360

        # blink dot
        self._blink_tick += 1
        if self._blink_tick % 14 == 0:
            self._blink = not self._blink

        # auto-cycle state for demo: idle→listening→speaking→idle
        self._cycle_tick += 1
        if   self._cycle_tick < 120:  self.state = "idle"
        elif self._cycle_tick < 280:  self.state = "listening"
        elif self._cycle_tick < 460:  self.state = "speaking"
        else:                          self._cycle_tick = 0

        # update waveform bar heights
        import random as _rnd
        for i in range(len(self._wave)):
            if self.state == "speaking":
                tgt = _rnd.uniform(0.12, 1.0)
            elif self.state == "listening":
                tgt = 0.04 + 0.18 * abs(math.sin(self._tick * 0.09 + i * 0.55))
            else:
                tgt = 0.02 + 0.03 * abs(math.sin(self._tick * 0.04 + i * 0.3))
            self._wave[i] += (tgt - self._wave[i]) * 0.25

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        # Offset cx to compensate for asymmetric panel widths (left=224, right=288)
        cx = W // 2 + (RIGHT_W - LEFT_W) // 2
        cy = H // 2

        # Background
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(BG))
        p.drawRect(0, 0, W, H)

        # Subtle radial gradient overlay
        rg = QRadialGradient(QPointF(cx, cy), min(W, H) // 2)
        rg.setColorAt(0, _c(0, 45, 75, 28))
        rg.setColorAt(1, _c(0, 0,  0,   0))
        p.setBrush(QBrush(rg)); p.drawRect(0, 0, W, H)

        # ── Concentric segmented rings ──────────────────────────────────────
        #   (radius, n_segs, gap_deg, linewidth, base_alpha, prominent)
        rings = [
            (172, 48,  3, 0.9, 28, False),
            (154, 12,  8, 2.2, 55, True ),
            (136, 64,  2, 0.8, 26, False),
            (118, 24,  5, 1.5, 44, False),
            (100,  8,  8, 2.8, 80, True ),
            ( 82, 40,  4, 1.0, 38, False),
            ( 64, 16,  6, 2.2, 68, True ),
        ]

        for i, (r, nseg, gap, lw, base_a, prom) in enumerate(rings):
            rot     = self._rot[i]
            seg_deg = 360 / nseg
            arc_deg = seg_deg - gap
            ab = int(self._audio * 38) if prom else 0
            a  = min(255, base_a + ab)
            rect = QRectF(cx - r, cy - r, r*2, r*2)

            if prom:
                p.setPen(QPen(pri(a // 5), lw * 5,
                              Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                for j in range(nseg):
                    s  = int((rot + j*seg_deg) * 16)
                    sp = int(arc_deg * 16)
                    p.drawArc(rect, s, sp)

            p.setPen(QPen(pri(a), lw,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            for j in range(nseg):
                s  = int((rot + j*seg_deg) * 16)
                sp = int(arc_deg * 16)
                p.drawArc(rect, s, sp)

        # ── Pulse waves from center ─────────────────────────────────────────
        lim = 210.0
        for pr in self._pulses:
            a = max(0, int(200 * (1.0 - pr / lim)))
            p.setPen(QPen(pri(a), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), pr, pr)

        # ── Tick marks on outer ring (short radial lines) ────────────────────
        t_r_out = 174.0   # just outside outermost ring
        t_r_in  = t_r_out - 7   # short tick
        t_r_lng = t_r_out - 13  # long tick (every 30°)
        p.setPen(QPen(pri(90), 1))
        for deg in range(0, 360, 6):
            rad = math.radians(deg)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            inn = t_r_lng if deg % 30 == 0 else t_r_in
            p.drawLine(
                QPointF(cx + t_r_out * cos_r, cy - t_r_out * sin_r),
                QPointF(cx + inn      * cos_r, cy - inn      * sin_r),
            )

        # ── Tick marks on middle prominent ring (r≈100) ───────────────────────
        m_r_out = 102.0
        p.setPen(QPen(pri(70), 1))
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            inn = m_r_out - 10 if deg % 45 == 0 else m_r_out - 5
            p.drawLine(
                QPointF(cx + m_r_out * cos_r, cy - m_r_out * sin_r),
                QPointF(cx + inn     * cos_r, cy - inn     * sin_r),
            )

        # ── Scanner arcs (rotating short arcs between tick marks) ────────────
        # (radius, scan_idx, arc_len_deg, linewidth, color_fn)
        scanners = [
            (174, 0, 38, 2.2, pri),   # outer ring, cyan, CW
            (174, 1, 22, 1.5, pri),   # outer ring, cyan, CCW
            (136, 2, 52, 1.8, amb),   # mid ring, amber, fast CW
            (154, 3, 28, 1.2, pri),   # second ring, cyan, CCW
        ]
        sa = int(160 + 60 * self._audio)
        for r, si, arc_len, lw, col_fn in scanners:
            rect = QRectF(cx - r, cy - r, r*2, r*2)
            # glow
            p.setPen(QPen(col_fn(sa // 5), lw * 4,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(rect, int(self._scan[si] * 16), int(arc_len * 16))
            # main arc
            p.setPen(QPen(col_fn(sa), lw,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(rect, int(self._scan[si] * 16), int(arc_len * 16))

        # ── Cardinal targeting markers ──────────────────────────────────────
        for angle, lbl in [(90, "N"), (0, "E"), (270, "S"), (180, "W")]:
            a_rad = math.radians(angle)
            mx = cx + int(100 * math.cos(a_rad))
            my = cy - int(100 * math.sin(a_rad))
            p.setPen(QPen(pri(115), 1)); p.setBrush(QBrush(pri(28)))
            p.drawEllipse(QPointF(mx, my), 5.5, 5.5)
            p.setFont(F(7, True)); p.setPen(pri(185))
            p.drawText(mx - 3, my + 4, lbl)

        # ── Inner orb (audio reactive) ──────────────────────────────────────
        orb_r = 38 + self._audio * 10
        rg2   = QRadialGradient(QPointF(cx, cy), orb_r)
        rg2.setColorAt(0.00, pri(210))
        rg2.setColorAt(0.35, pri(70))
        rg2.setColorAt(0.75, pri(14))
        rg2.setColorAt(1.00, pri(0))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(rg2))
        p.drawEllipse(QPointF(cx, cy), orb_r, orb_r)

        # Inner fixed ring
        p.setPen(QPen(pri(155), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 19, 19)

        # ── Wave rings (audio visualization) ───────────────────────────────
        for i in range(4):
            wr = 21 + i*9 + self._audio * 15
            wa = max(0, int(125 - i*28))
            p.setPen(QPen(pri(wa), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), wr, wr)

        # Center dot
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(PRI))
        p.drawEllipse(QPointF(cx, cy), 3, 3)

        # ── Waveform bar chart (bottom of HUD) ──────────────────────────────
        N     = len(self._wave)
        bw    = 7
        max_h = 44
        wx0   = cx - N * bw // 2
        wy    = H - 18                  # baseline y

        for i, h_frac in enumerate(self._wave):
            hgt = max(2, int(h_frac * max_h))
            if self.state == "speaking":
                col = PRI if h_frac > 0.55 else pri(110)
            elif self.state == "listening":
                col = pri(130)
            else:
                col = pri(50)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(col))
            p.drawRect(QRectF(wx0 + i * bw, wy - hgt, bw - 1, hgt))

        # baseline line
        p.setPen(QPen(pri(35), 1))
        p.drawLine(int(wx0), wy, int(wx0 + N * bw), wy)

        # ── LISTENING / SPEAKING indicator (above waveform) ─────────────────
        if self.state == "speaking":
            dot_col = AMB; lbl_text = "SPEAKING"
        elif self.state == "listening":
            dot_col = SUC; lbl_text = "LISTENING"
        else:
            dot_col = pri(55); lbl_text = "STANDBY"

        sym   = "●" if self._blink else "○"
        ind_y = wy - max_h - 16
        p.setFont(F(10, True)); p.setPen(dot_col)
        lbl_full = f"{sym}  {lbl_text}"
        fm = QFontMetrics(p.font())
        p.drawText(cx - fm.horizontalAdvance(lbl_full) // 2, ind_y, lbl_full)

        # HUD label top
        p.setFont(F(7)); p.setPen(pri(75))
        top_lbl = "SYSTEM TRACKING"
        fm2 = QFontMetrics(p.font())
        p.drawText(cx - fm2.horizontalAdvance(top_lbl) // 2, cy - 185, top_lbl)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# SystemStatusCard — system online/offline indicator card
# ══════════════════════════════════════════════════════════════════════════════
class SystemStatusCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self.setFixedHeight(56)
        t = QTimer(self); t.timeout.connect(self._step); t.start(60)

    def _step(self): self._tick += 1; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Card bg
        p.setPen(QPen(pri(28), 1))
        p.setBrush(QBrush(_c(8, 19, 34, 215)))
        p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 7, 7)

        # Section label
        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(10, 16, "SYSTEM STATUS")

        # Pulsing status dot
        da = int(210 + 45 * math.sin(self._tick * 0.10))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(suc(da)))
        p.drawEllipse(QRectF(10, 23, 10, 10))

        # Pulse ring around dot
        pr_r = 7 + 3 * math.sin(self._tick * 0.10)
        pa   = int(80 + 60 * abs(math.sin(self._tick * 0.10)))
        p.setPen(QPen(suc(pa), 0.8)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(15, 28), pr_r, pr_r)

        # Status label
        p.setFont(F(11, True)); p.setPen(SUC)
        p.drawText(27, 35, "ONLINE")

        # Version + uptime row
        p.setFont(F(7)); p.setPen(pri(110))
        p.drawText(10, H - 8, "B.1.0.0")
        p.setFont(F(7)); p.setPen(pri(65))
        p.drawText(W // 2, H - 8, "GEMINI API")

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# WorldMapWidget — flat equirectangular world map, no card background
# ══════════════════════════════════════════════════════════════════════════════
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
        lbl_h = 13          # top label height
        mx, my = 2, lbl_h  # map margins
        mh = H - my - 10   # map height area

        def proj(lon, lat):
            x = mx + (lon + 180) / 360 * (W - 2 * mx)
            y = my + (90 - lat) / 180 * mh
            return QPointF(x, y)

        # Subtle grid lines
        p.setPen(QPen(pri(10), 0.5))
        for lon in range(-180, 181, 45):
            pt1 = proj(lon, 90); pt2 = proj(lon, -90)
            p.drawLine(pt1, pt2)
        for lat in range(-60, 61, 30):
            pt1 = proj(-180, lat); pt2 = proj(180, lat)
            p.drawLine(pt1, pt2)

        # Equatorial line
        eq1 = proj(-180, 0); eq2 = proj(180, 0)
        p.setPen(QPen(pri(20), 0.6, Qt.PenStyle.DashLine))
        p.drawLine(eq1, eq2)

        # Continent fills + outlines
        for poly in _WORLD_POLYS:
            path = QPainterPath()
            for i, (lon, lat) in enumerate(poly):
                pt = proj(lon, lat)
                if i == 0: path.moveTo(pt)
                else:       path.lineTo(pt)
            path.closeSubpath()
            p.setBrush(QBrush(pri(12)))
            p.setPen(QPen(pri(65), 0.7))
            p.drawPath(path)

        # KL location marker (3.14°N, 101.69°E)
        kl = proj(101.69, 3.14)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(AMB))
        p.drawEllipse(kl, 3.2, 3.2)
        pr_r = 5.5 + 3.5 * math.sin(self._tick * 0.13)
        pa   = int(160 + 80 * math.sin(self._tick * 0.13))
        p.setPen(QPen(amb(pa // 2), 0.9)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(kl, pr_r, pr_r)

        # Labels
        p.setFont(F(7)); p.setPen(DIM)
        p.drawText(0, 11, "LOCATION  TRACKING")
        p.setFont(F(7)); p.setPen(amb(175))
        p.drawText(0, H, "03°08′N  101°42′E")

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# LeftPanel — Globe (top) · CPU · RAM · SSD
# ══════════════════════════════════════════════════════════════════════════════
class LeftPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(LEFT_W)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(5)

        if HAS_PSUTIL:
            def cpu():
                v = psutil.cpu_percent() / 100
                return v, f"{int(v*100)}%"
            def ram():
                v = psutil.virtual_memory().percent / 100
                return v, f"{int(v*100)}%"
            def disk():
                try:    v = psutil.disk_usage('/').percent / 100
                except: v = 0.42
                return v, f"{int(v*100)}%"
        else:
            def cpu():  return 0.45, "45%"
            def ram():  return 0.62, "62%"
            def disk(): return 0.38, "38%"

        lay.addWidget(WorldMapWidget())   # world map at top, no card bg
        lay.addWidget(SystemStatusCard())
        lay.addWidget(MetricCard("CORE PROC", cpu,  PRI))
        lay.addWidget(MetricCard("MEM ARRAY", ram,  AMB))
        lay.addWidget(MetricCard("STORAGE",   disk, SUC))
        lay.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# RightMetricsPanel — Network · Comms · Session (permanent right side)
# ══════════════════════════════════════════════════════════════════════════════
class RightMetricsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(RIGHT_W)
        self._nt = [0]

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(5)

        def net():
            self._nt[0] += 1
            v = 0.18 + 0.42 * abs(math.sin(self._nt[0] * 0.08))
            return v, f"{int(v*999)}K"

        lay.addWidget(MetricCard("COMMS BW",  net,  pri(220)))
        lay.addWidget(CommsCard())
        lay.addWidget(SessionCard())
        lay.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# FileDropCard — upload area widget
# ══════════════════════════════════════════════════════════════════════════════
class FileDropCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self._tick  = 0
        self.setFixedHeight(80)
        self.setAcceptDrops(True)
        t = QTimer(self); t.timeout.connect(self._step); t.start(60)

    def _step(self): self._tick += 1; self.update()

    def enterEvent(self, _): self._hover = True;  self.update()
    def leaveEvent(self, _): self._hover = False; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        alpha = int(45 + 30 * math.sin(self._tick * 0.1)) if not self._hover else 90
        p.setPen(QPen(pri(alpha), 1, Qt.PenStyle.DashLine))
        p.setBrush(QBrush(_c(0, 212, 255, 8 if not self._hover else 18)))
        p.drawRoundedRect(QRectF(2, 2, W-4, H-4), 7, 7)

        p.setFont(F(8)); p.setPen(pri(alpha + 40))
        lbl = "⬡  DROP FILE HERE"
        fm  = QFontMetrics(p.font())
        p.drawText((W - fm.horizontalAdvance(lbl)) // 2, H//2 + 3, lbl)

        p.setFont(F(7)); p.setPen(DIM)
        sub = "or click to browse"
        fm2 = QFontMetrics(p.font())
        p.drawText((W - fm2.horizontalAdvance(sub)) // 2, H//2 + 18, sub)
        p.end()

    def mousePressEvent(self, _):
        pass   # would open file dialog in real impl


# ══════════════════════════════════════════════════════════════════════════════
# ActivityPanel — activity log + file upload + chat input (toggle overlay)
# ══════════════════════════════════════════════════════════════════════════════
class ActivityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(RIGHT_W)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        # ── Activity Log ──────────────────────────────────────────────────────
        lbl_log = QLabel("◈  ACTIVITY LOG")
        lbl_log.setFont(F(9, True))
        lbl_log.setStyleSheet(f"color: {PRI.name()};")
        lay.addWidget(lbl_log)

        log = QTextEdit()
        log.setReadOnly(True)
        log.setFont(F(11))
        log.setStyleSheet("""
            QTextEdit {
                background: rgba(8,19,34,215);
                color: rgba(200,232,248,175);
                border: 1px solid rgba(0,212,255,28);
                border-radius: 7px;
                padding: 8px;
            }
            QScrollBar:vertical { width: 4px; background: rgba(0,0,0,0); }
            QScrollBar::handle:vertical { background: rgba(0,212,255,60); border-radius: 2px; }
        """)
        log.setPlainText(
            "[14:32:01]  System initialized\n"
            "[14:32:03]  Gemini API connected\n"
            "[14:32:05]  Microphone active\n"
            "[14:32:08]  Voice session started\n"
            "[14:32:12]  USER: Hello Viko\n"
            "[14:32:13]  VIKO: Hello! How can I help?\n"
            "[14:32:20]  USER: Show me metrics\n"
            "[14:32:21]  VIKO: Displaying system metrics\n"
            "[14:32:35]  USER: What's the weather?\n"
            "[14:32:36]  VIKO: 28°C, Partly Cloudy\n"
        )
        lay.addWidget(log, 1)

        # ── File Upload ───────────────────────────────────────────────────────
        lbl_file = QLabel("⬡  FILE UPLOAD")
        lbl_file.setFont(F(9, True))
        lbl_file.setStyleSheet(f"color: {AMB.name()};")
        lay.addWidget(lbl_file)

        lay.addWidget(FileDropCard())

        # ── Chat Input ────────────────────────────────────────────────────────
        lbl_chat = QLabel("◎  COMMAND INPUT")
        lbl_chat.setFont(F(9, True))
        lbl_chat.setStyleSheet(f"color: {PRI.name()};")
        lay.addWidget(lbl_chat)

        input_row = QWidget()
        ilay = QHBoxLayout(input_row)
        ilay.setContentsMargins(0, 0, 0, 0)
        ilay.setSpacing(6)

        chat_in = QLineEdit()
        chat_in.setPlaceholderText("Type a command...")
        chat_in.setFont(F(9))
        chat_in.setStyleSheet("""
            QLineEdit {
                background: rgba(8,19,34,215);
                color: rgba(200,232,248,200);
                border: 1px solid rgba(0,212,255,50);
                border-radius: 6px;
                padding: 6px 8px;
            }
            QLineEdit:focus { border-color: rgba(0,212,255,140); }
        """)
        ilay.addWidget(chat_in, 1)

        send_btn = QPushButton("▶")
        send_btn.setFixedSize(32, 32)
        send_btn.setFont(F(8, True))
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,212,255,25);
                color: {PRI.name()};
                border: 1px solid rgba(0,212,255,80);
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: rgba(0,212,255,55); }}
            QPushButton:pressed {{ background: rgba(0,212,255,80); }}
        """)
        ilay.addWidget(send_btn)
        lay.addWidget(input_row)


# ══════════════════════════════════════════════════════════════════════════════
# Main Window
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VIKO — JARVIS Modern HUD  ·  Design Preview v1")
        self.resize(WIN_W, WIN_H)
        self.setStyleSheet("background: rgb(0,0,0); color: rgb(200,232,248);")
        self._build()

    def _build(self):
        self._state = {"panel_visible": False}

        root = QWidget()
        self.setCentralWidget(root)
        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Header
        vlay.addWidget(FloatingArc(_hdr_draw, HDR_H, flip=False, state=self._state))

        # Body
        body = QWidget()
        blay = QHBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(0)

        blay.addWidget(LeftPanel())
        blay.addWidget(HudCanvas(), 1)

        # Right column: toggle button (top) + stacked panels (below)
        right_col = QWidget()
        right_col.setFixedWidth(RIGHT_W)
        rcol_lay = QVBoxLayout(right_col)
        rcol_lay.setContentsMargins(0, 0, 0, 0)
        rcol_lay.setSpacing(0)

        # Top button bar — fullscreen + panel toggle, aligned with panel content
        btn_bar = QWidget()
        btn_bar.setFixedHeight(32)
        btn_bar_lay = QHBoxLayout(btn_bar)
        btn_bar_lay.setContentsMargins(8, 4, 8, 0)
        btn_bar_lay.setSpacing(4)

        _btn_ss_base = lambda active=False: f"""
            QPushButton {{
                background: {'rgba(0,212,255,30)' if active else 'rgba(0,212,255,12)'};
                color: {PRI.name() if active else pri(140).name()};
                border: 1px solid {'rgba(0,212,255,110)' if active else 'rgba(0,212,255,40)'};
                border-radius: 4px;
                padding: 0 6px;
            }}
            QPushButton:hover {{
                background: rgba(0,212,255,40);
                color: {PRI.name()};
                border-color: rgba(0,212,255,130);
            }}
        """

        # Fullscreen button
        self._fs_btn = QPushButton("⛶")
        self._fs_btn.setFixedSize(28, 26)
        self._fs_btn.setFont(F(9, True))
        self._fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fs_btn.setToolTip("Toggle Fullscreen")
        self._fs_btn.setStyleSheet(_btn_ss_base())
        self._fs_btn.clicked.connect(self._toggle_fullscreen)
        btn_bar_lay.addWidget(self._fs_btn)

        # Panel toggle button
        self._toggle_btn = QPushButton("◧  ACTIVITY")
        self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.setFont(F(8, True))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(_btn_ss_base())
        self._toggle_btn.clicked.connect(self._toggle_panel)
        btn_bar_lay.addWidget(self._toggle_btn, 1)

        self._btn_ss_base = _btn_ss_base
        rcol_lay.addWidget(btn_bar)

        # Stacked panels below button
        self._right_stack = QStackedWidget()
        self._right_stack.addWidget(RightMetricsPanel())   # index 0 (default)
        self._right_stack.addWidget(ActivityPanel())       # index 1 (toggle)
        self._right_stack.setCurrentIndex(0)
        rcol_lay.addWidget(self._right_stack, 1)

        blay.addWidget(right_col)
        vlay.addWidget(body, 1)

        # Footer — PANEL button wired to toggle
        self._ftr = FloatingArc(_ftr_draw, FTR_H, flip=True,
                                on_click=self._toggle_panel, state=self._state)
        vlay.addWidget(self._ftr)

    def _toggle_panel(self):
        self._state["panel_visible"] = not self._state["panel_visible"]
        visible = self._state["panel_visible"]
        self._right_stack.setCurrentIndex(1 if visible else 0)
        self._toggle_btn.setText("◨  METRICS" if visible else "◧  ACTIVITY")
        self._toggle_btn.setStyleSheet(self._btn_ss_base(visible))
        self._ftr.update()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self._fs_btn.setStyleSheet(self._btn_ss_base(False))
        else:
            self.showFullScreen()
            self._fs_btn.setStyleSheet(self._btn_ss_base(True))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
