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


class HudCanvas(QWidget):
    """Concentric segmented rings, scanner arcs, pulse waves, waveform, state indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick   = 0
        self._audio  = 0.0
        self._rot    = [0.0] * 7
        self._spd    = [0.28, -0.44, 0.20, -0.36, 0.52, -0.22, 0.12]
        self._pulses: list[float] = [0.0, 80.0, 160.0]
        self._scan     = [0.0, 180.0, 90.0, 270.0]
        self._scan_spd = [1.4, -0.9, 2.1, -1.6]
        self.state       = "idle"      # "idle" | "listening" | "speaking" | "thinking"
        self._muted      = False
        self._blink      = True
        self._blink_tick = 0
        import random as _rnd
        self._rnd = _rnd
        N = 48
        self._wave = [0.0] * N
        self.setMinimumSize(320, 320)
        t = QTimer(self); t.timeout.connect(self._step); t.start(40)

    def set_state(self, state: str):
        """Accept viko.py state strings and map to animation state."""
        s = state.upper()
        if s == "SPEAKING":     self.state = "speaking"
        elif s == "LISTENING":  self.state = "listening"
        elif s == "THINKING":   self.state = "listening"   # same animation
        elif s == "MUTED":      self._muted = True; self.state = "idle"
        else:                   self.state = "idle"
        if s != "MUTED":        self._muted = False

    def set_audio_level(self, rms: float):
        """Feed real RMS (0..1) from mic callback; falls back to simulated."""
        self._audio = min(1.0, rms * 3)

    def _step(self):
        self._tick += 1
        if self._audio < 0.01:   # simulate when no real audio
            self._audio = 0.30 + 0.28 * abs(math.sin(self._tick * 0.07))
        for i in range(7):
            self._rot[i] = (self._rot[i] + self._spd[i]) % 360
        lim = 210.0
        spd = 1.8 + self._audio * 0.8
        self._pulses = [r + spd for r in self._pulses if r + spd < lim]
        if len(self._pulses) < 4 and self._tick % 38 == 0:
            self._pulses.append(0.0)
        for i in range(4):
            self._scan[i] = (self._scan[i] + self._scan_spd[i]) % 360
        self._blink_tick += 1
        if self._blink_tick % 14 == 0:
            self._blink = not self._blink
        for i in range(len(self._wave)):
            if self.state == "speaking":
                tgt = self._rnd.uniform(0.12, 1.0)
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
        cx = W // 2 + (RIGHT_W - LEFT_W) // 2
        cy = H // 2

        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(BG))
        p.drawRect(0, 0, W, H)
        rg = QRadialGradient(QPointF(cx, cy), min(W, H) // 2)
        rg.setColorAt(0, _c(0, 45, 75, 28)); rg.setColorAt(1, _c(0, 0, 0, 0))
        p.setBrush(QBrush(rg)); p.drawRect(0, 0, W, H)

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
            rot = self._rot[i]; seg_deg = 360 / nseg; arc_deg = seg_deg - gap
            ab = int(self._audio * 38) if prom else 0
            a  = min(255, base_a + ab)
            rect = QRectF(cx - r, cy - r, r * 2, r * 2)
            if prom:
                p.setPen(QPen(pri(a // 5), lw * 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                for j in range(nseg):
                    p.drawArc(rect, int((rot + j * seg_deg) * 16), int(arc_deg * 16))
            p.setPen(QPen(pri(a), lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            for j in range(nseg):
                p.drawArc(rect, int((rot + j * seg_deg) * 16), int(arc_deg * 16))

        lim = 210.0
        for pr in self._pulses:
            a = max(0, int(200 * (1.0 - pr / lim)))
            p.setPen(QPen(pri(a), 1.2)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), pr, pr)

        t_r_out = 174.0; t_r_in = t_r_out - 7; t_r_lng = t_r_out - 13
        p.setPen(QPen(pri(90), 1))
        for deg in range(0, 360, 6):
            rad = math.radians(deg); cos_r, sin_r = math.cos(rad), math.sin(rad)
            inn = t_r_lng if deg % 30 == 0 else t_r_in
            p.drawLine(QPointF(cx + t_r_out * cos_r, cy - t_r_out * sin_r),
                       QPointF(cx + inn * cos_r, cy - inn * sin_r))
        m_r_out = 102.0; p.setPen(QPen(pri(70), 1))
        for deg in range(0, 360, 15):
            rad = math.radians(deg); cos_r, sin_r = math.cos(rad), math.sin(rad)
            inn = m_r_out - 10 if deg % 45 == 0 else m_r_out - 5
            p.drawLine(QPointF(cx + m_r_out * cos_r, cy - m_r_out * sin_r),
                       QPointF(cx + inn * cos_r, cy - inn * sin_r))

        scanners = [(174,0,38,2.2,pri),(174,1,22,1.5,pri),(136,2,52,1.8,amb),(154,3,28,1.2,pri)]
        sa = int(160 + 60 * self._audio)
        for r, si, arc_len, lw, col_fn in scanners:
            rect = QRectF(cx - r, cy - r, r * 2, r * 2)
            p.setPen(QPen(col_fn(sa // 5), lw * 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(rect, int(self._scan[si] * 16), int(arc_len * 16))
            p.setPen(QPen(col_fn(sa), lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(rect, int(self._scan[si] * 16), int(arc_len * 16))

        for angle, lbl in [(90,"N"),(0,"E"),(270,"S"),(180,"W")]:
            a_rad = math.radians(angle)
            mx2 = cx + int(100 * math.cos(a_rad)); my2 = cy - int(100 * math.sin(a_rad))
            p.setPen(QPen(pri(115), 1)); p.setBrush(QBrush(pri(28)))
            p.drawEllipse(QPointF(mx2, my2), 5.5, 5.5)
            p.setFont(F(7, True)); p.setPen(pri(185))
            p.drawText(mx2 - 3, my2 + 4, lbl)

        orb_r = 38 + self._audio * 10
        rg2 = QRadialGradient(QPointF(cx, cy), orb_r)
        rg2.setColorAt(0.00, pri(210)); rg2.setColorAt(0.35, pri(70))
        rg2.setColorAt(0.75, pri(14)); rg2.setColorAt(1.00, pri(0))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(rg2))
        p.drawEllipse(QPointF(cx, cy), orb_r, orb_r)
        p.setPen(QPen(pri(155), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 19, 19)
        for i in range(4):
            wr = 21 + i * 9 + self._audio * 15; wa = max(0, int(125 - i * 28))
            p.setPen(QPen(pri(wa), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), wr, wr)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(PRI))
        p.drawEllipse(QPointF(cx, cy), 3, 3)

        N = len(self._wave); bw = 7; max_h = 44
        wx0 = cx - N * bw // 2; wy = H - 18
        for i, h_frac in enumerate(self._wave):
            hgt = max(2, int(h_frac * max_h))
            if self.state == "speaking":    col = PRI if h_frac > 0.55 else pri(110)
            elif self.state == "listening": col = pri(130)
            else:                           col = pri(50)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(col))
            p.drawRect(QRectF(wx0 + i * bw, wy - hgt, bw - 1, hgt))
        p.setPen(QPen(pri(35), 1))
        p.drawLine(int(wx0), wy, int(wx0 + N * bw), wy)

        if self.state == "speaking":    dot_col = AMB; lbl_text = "SPEAKING"
        elif self.state == "listening": dot_col = SUC; lbl_text = "LISTENING"
        else:                           dot_col = pri(55); lbl_text = "STANDBY"
        if self._muted: dot_col = _c(255, 68, 68); lbl_text = "MUTED"

        sym = "●" if self._blink else "○"
        ind_y = wy - max_h - 16
        p.setFont(F(10, True)); p.setPen(dot_col)
        lbl_full = f"{sym}  {lbl_text}"
        fm = QFontMetrics(p.font())
        p.drawText(cx - fm.horizontalAdvance(lbl_full) // 2, ind_y, lbl_full)

        p.setFont(F(7)); p.setPen(pri(75))
        top_lbl = "SYSTEM TRACKING"
        fm2 = QFontMetrics(p.font())
        p.drawText(cx - fm2.horizontalAdvance(top_lbl) // 2, cy - 185, top_lbl)
        p.end()
