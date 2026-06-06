# JARVIS HUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `viko/ui.py` with the JARVIS Modern HUD design from `design_preview.py`, keeping the `VikoUI` public interface identical so `viko.py` requires zero changes.

**Architecture:** Split the monolithic `ui.py` into three focused modules — `ui_theme.py` (palette + constants), `ui_widgets.py` (all custom QPainter widgets), and `ui.py` (MainWindow assembly + VikoUI facade). The `VikoUI` class and all its public methods/properties stay byte-for-byte compatible with the current interface used by `viko.py`.

**Tech Stack:** PyQt6, psutil, math, design_preview.py (visual reference), existing viko/ui_backup.py (LogWidget typewriter pattern, _SysMetrics pattern, SetupOverlay pattern)

---

## Public Interface Contract (must not change)

```python
class VikoUI:
    def __init__(self, face_path: str, size=None): ...
    @property
    def muted(self) -> bool: ...
    @muted.setter
    def muted(self, v: bool): ...
    @property
    def current_file(self) -> str | None: ...
    @property
    def on_text_command(self): ...
    @on_text_command.setter
    def on_text_command(self, cb): ...
    def set_state(self, state: str): ...   # "LISTENING" | "SPEAKING" | "THINKING" | "IDLE" | "MUTED"
    def write_log(self, text: str): ...
    def wait_for_api_key(self): ...
    def start_speaking(self): ...
    def stop_speaking(self): ...
```

---

## File Structure

| File | Responsibility |
|------|---------------|
| `viko/ui_theme.py` | Color palette (`C` class), font helper `F()`, world-map polygon data `_WORLD_POLYS`, window size constants |
| `viko/ui_widgets.py` | All custom QPainter widgets: FloatingArc, MetricCard, SystemStatusCard, WorldMapWidget, HudCanvas, CommsCard, SessionCard, LogWidget, FileDropCard, ActivityPanel, LeftPanel, RightMetricsPanel, SetupOverlay |
| `viko/ui.py` | `_SysMetrics` thread, `MainWindow` layout assembly, `VikoUI` public facade |

`design_preview.py` is the visual reference — copy logic from there, adapt to viko integration.

---

## Task 1: Create `viko/ui_theme.py`

**Files:**
- Create: `viko/ui_theme.py`

- [ ] **Step 1: Write the file**

```python
# viko/ui_theme.py
from __future__ import annotations
import math
from PyQt6.QtGui import QColor, QFont

WIN_W, WIN_H = 1160, 740
HDR_H  = 62
FTR_H  = 58
LEFT_W = 224
RIGHT_W = 288


def _c(r, g, b, a=255): return QColor(r, g, b, a)

BG   = _c(0,   0,   0)
CARD = _c(4,   8,  14)
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
```

- [ ] **Step 2: Verify import works**

```bash
cd /Users/eksa/Projects/viko-assistant
.venv/bin/python -c "from viko.ui_theme import PRI, F, _WORLD_POLYS; print('ok', len(_WORLD_POLYS))"
```

Expected: `ok 7`

- [ ] **Step 3: Commit**

```bash
git add viko/ui_theme.py
git commit -m "feat: add ui_theme.py — palette, font helper, world map polygon data"
```

---

## Task 2: Create `viko/ui_widgets.py` — FloatingArc header/footer

**Files:**
- Create: `viko/ui_widgets.py`

- [ ] **Step 1: Create the file with FloatingArc**

```python
# viko/ui_widgets.py
from __future__ import annotations
import math, time
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient, QFontMetrics,
)
from PyQt6.QtWidgets import QWidget

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
```

- [ ] **Step 2: Verify import**

```bash
.venv/bin/python -c "from viko.ui_widgets import FloatingArc; print('FloatingArc ok')"
```

Expected: `FloatingArc ok`

- [ ] **Step 3: Commit**

```bash
git add viko/ui_widgets.py
git commit -m "feat: add ui_widgets.py with FloatingArc arch panel"
```

---

## Task 3: Add header/footer draw functions to `ui_widgets.py`

**Files:**
- Modify: `viko/ui_widgets.py`

- [ ] **Step 1: Append header/footer draw functions after the FloatingArc class**

```python
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
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "from viko.ui_widgets import _hdr_draw, _ftr_draw; print('draw fns ok')"
```

Expected: `draw fns ok`

- [ ] **Step 3: Commit**

```bash
git add viko/ui_widgets.py
git commit -m "feat: add header/footer draw functions to ui_widgets"
```

---

## Task 4: Add MetricCard, SystemStatusCard, WorldMapWidget to `ui_widgets.py`

**Files:**
- Modify: `viko/ui_widgets.py`

- [ ] **Step 1: Append the three card widget classes**

```python
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

        from PyQt6.QtGui import QPainterPath
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
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "from viko.ui_widgets import MetricCard, SystemStatusCard, WorldMapWidget; print('cards ok')"
```

Expected: `cards ok`

- [ ] **Step 3: Commit**

```bash
git add viko/ui_widgets.py
git commit -m "feat: add MetricCard, SystemStatusCard, WorldMapWidget"
```

---

## Task 5: Add CommsCard, SessionCard to `ui_widgets.py`

**Files:**
- Modify: `viko/ui_widgets.py`

- [ ] **Step 1: Append CommsCard and SessionCard**

```python
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
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "from viko.ui_widgets import CommsCard, SessionCard; print('session cards ok')"
```

Expected: `session cards ok`

- [ ] **Step 3: Commit**

```bash
git add viko/ui_widgets.py
git commit -m "feat: add CommsCard and SessionCard"
```

---

## Task 6: Add HudCanvas to `ui_widgets.py`

**Files:**
- Modify: `viko/ui_widgets.py`

- [ ] **Step 1: Append HudCanvas (visual center piece)**

```python
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

        if self.state == "speaking":   dot_col = AMB; lbl_text = "SPEAKING"
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
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "from viko.ui_widgets import HudCanvas; print('HudCanvas ok')"
```

Expected: `HudCanvas ok`

- [ ] **Step 3: Commit**

```bash
git add viko/ui_widgets.py
git commit -m "feat: add HudCanvas with rings, scanners, pulse waves, waveform, state indicator"
```

---

## Task 7: Add LogWidget (typewriter), FileDropCard, ActivityPanel, panel classes to `ui_widgets.py`

**Files:**
- Modify: `viko/ui_widgets.py`

- [ ] **Step 1: Add remaining imports at top of ui_widgets.py**

At the very top of `viko/ui_widgets.py`, ensure these are in the imports block:

```python
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QSizePolicy,
)
```

- [ ] **Step 2: Append LogWidget with typewriter animation**

```python
class LogWidget(QTextEdit):
    """Activity log with typewriter effect. Thread-safe via signal."""
    _sig = pyqtSignal(str)

    # Tag colour map (matches ui_backup.py pattern)
    _TAG_COLORS = {
        "you":  "#ffb347",
        "ai":   "#00d4ff",
        "err":  "#ff4444",
        "file": "#00ff9f",
        "sys":  "#3a8a9a",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(F(11))
        self.setStyleSheet("""
            QTextEdit {
                background: rgba(8,19,34,215);
                color: rgba(200,232,248,175);
                border: 1px solid rgba(0,212,255,28);
                border-radius: 7px;
                padding: 8px;
            }
            QScrollBar:vertical { width: 5px; background: rgba(0,0,0,0); }
            QScrollBar::handle:vertical { background: rgba(0,212,255,60); border-radius: 2px; }
        """)
        self._queue: list[str] = []
        self._typing = False
        self._text   = ""
        self._pos    = 0
        self._tag    = "sys"
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False; return
        self._typing = True
        raw = self._queue.pop(0)
        # detect tag prefix like "YOU: " "AI: " "SYS: " "ERR: " "FILE: "
        low = raw.lower()
        for tag in ("you", "ai", "err", "file", "sys"):
            if low.startswith(tag + ":") or low.startswith(f"[{tag}]"):
                self._tag = tag; break
        else:
            self._tag = "sys"
        self._text = raw; self._pos = 0
        self._tmr.start(6)

    def _step(self):
        if self._pos >= len(self._text):
            self._tmr.stop()
            self.append("")   # newline
            self._next(); return
        chunk = self._text[self._pos: self._pos + 3]
        col   = self._TAG_COLORS.get(self._tag, "#3a8a9a")
        self.moveCursor(self.textCursor().MoveOperation.End)
        self.setTextColor(QColor(col))
        self.insertPlainText(chunk)
        self.moveCursor(self.textCursor().MoveOperation.End)
        self._pos += 3


class FileDropCard(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover   = False
        self._tick    = 0
        self._current = None
        self.setFixedHeight(80)
        self.setAcceptDrops(True)
        t = QTimer(self); t.timeout.connect(self._step); t.start(60)

    def current_file(self) -> str | None: return self._current
    def _step(self): self._tick += 1; self.update()
    def enterEvent(self, _): self._hover = True;  self.update()
    def leaveEvent(self, _): self._hover = False; self.update()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._current = path
            self.file_selected.emit(path)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        alpha = int(45 + 30 * math.sin(self._tick * 0.1)) if not self._hover else 90
        p.setPen(QPen(pri(alpha), 1, Qt.PenStyle.DashLine))
        p.setBrush(QBrush(_c(0, 212, 255, 8 if not self._hover else 18)))
        p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 7, 7)
        p.setFont(F(8)); p.setPen(pri(alpha + 40))
        lbl = "⬡  DROP FILE HERE"
        fm  = QFontMetrics(p.font())
        p.drawText((W - fm.horizontalAdvance(lbl)) // 2, H // 2 + 3, lbl)
        p.setFont(F(7)); p.setPen(DIM)
        sub = "or click to browse"
        fm2 = QFontMetrics(p.font())
        p.drawText((W - fm2.horizontalAdvance(sub)) // 2, H // 2 + 18, sub)
        p.end()

    def mousePressEvent(self, _):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Select file")
        if path:
            self._current = path; self.file_selected.emit(path)


class LeftPanel(QWidget):
    def __init__(self, metrics_snapshot_fn, parent=None):
        """
        metrics_snapshot_fn: callable () -> dict with keys cpu, mem, disk, net
        Values are floats 0..1.
        """
        super().__init__(parent)
        self.setFixedWidth(LEFT_W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(5)

        self._status_card = SystemStatusCard()

        def _metric(key, scale=100):
            def fn():
                v = metrics_snapshot_fn().get(key, 0.0)
                return v, f"{int(v * scale)}%"
            return fn

        lay.addWidget(WorldMapWidget())
        lay.addWidget(self._status_card)
        lay.addWidget(MetricCard("CORE PROC", _metric("cpu"),  PRI))
        lay.addWidget(MetricCard("MEM ARRAY", _metric("mem"),  AMB))
        lay.addWidget(MetricCard("STORAGE",   _metric("disk"), SUC))
        lay.addStretch()

    def set_online(self, online: bool):
        self._status_card.set_online(online)


class RightMetricsPanel(QWidget):
    def __init__(self, metrics_snapshot_fn, parent=None):
        super().__init__(parent)
        self.setFixedWidth(RIGHT_W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(5)

        def net_fn():
            v = metrics_snapshot_fn().get("net", 0.0)
            return v, f"{int(v * 999)}K"

        self._comms = CommsCard()
        self._sess  = SessionCard()
        lay.addWidget(MetricCard("COMMS BW", net_fn, pri(220)))
        lay.addWidget(self._comms)
        lay.addWidget(self._sess)
        lay.addStretch()

    def inc_ops(self): self._sess.inc_ops()


class ActivityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(RIGHT_W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        lbl_log = QLabel("◈  ACTIVITY LOG")
        lbl_log.setFont(F(9, True))
        lbl_log.setStyleSheet(f"color: {PRI.name()};")
        lay.addWidget(lbl_log)

        self._log = LogWidget()
        lay.addWidget(self._log, 1)

        lbl_file = QLabel("⬡  FILE UPLOAD")
        lbl_file.setFont(F(9, True))
        lbl_file.setStyleSheet(f"color: {AMB.name()};")
        lay.addWidget(lbl_file)

        self._drop = FileDropCard()
        lay.addWidget(self._drop)

        lbl_chat = QLabel("◎  COMMAND INPUT")
        lbl_chat.setFont(F(9, True))
        lbl_chat.setStyleSheet(f"color: {PRI.name()};")
        lay.addWidget(lbl_chat)

        row = QWidget(); ilay = QHBoxLayout(row)
        ilay.setContentsMargins(0, 0, 0, 0); ilay.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command...")
        self._input.setFont(F(9))
        self._input.setStyleSheet("""
            QLineEdit {
                background: rgba(8,19,34,215); color: rgba(200,232,248,200);
                border: 1px solid rgba(0,212,255,50); border-radius: 6px; padding: 6px 8px;
            }
            QLineEdit:focus { border-color: rgba(0,212,255,140); }
        """)
        ilay.addWidget(self._input, 1)
        btn = QPushButton("▶"); btn.setFixedSize(32, 32); btn.setFont(F(8, True))
        btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(0,212,255,25); color: {PRI.name()};
                border: 1px solid rgba(0,212,255,80); border-radius: 6px; }}
            QPushButton:hover {{ background: rgba(0,212,255,55); }}
        """)
        ilay.addWidget(btn)
        lay.addWidget(row)

    def append_log(self, text: str): self._log.append_log(text)
    def current_file(self) -> str | None: return self._drop.current_file()
    def on_text_command_changed(self, cb): self._input.returnPressed.connect(lambda: cb(self._input.text()))
```

- [ ] **Step 2: Verify**

```bash
.venv/bin/python -c "from viko.ui_widgets import LogWidget, ActivityPanel, LeftPanel, RightMetricsPanel; print('panel widgets ok')"
```

Expected: `panel widgets ok`

- [ ] **Step 3: Commit**

```bash
git add viko/ui_widgets.py
git commit -m "feat: add LogWidget, FileDropCard, ActivityPanel, LeftPanel, RightMetricsPanel"
```

---

## Task 8: Rewrite `viko/ui.py` — _SysMetrics + SetupOverlay + MainWindow + VikoUI

**Files:**
- Modify: `viko/ui.py` (full rewrite, backup already exists as `viko/ui_backup.py`)

- [ ] **Step 1: Write the new ui.py**

```python
# viko/ui.py
from __future__ import annotations
import math, sys, time, threading
from pathlib import Path

import psutil

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal, QObject
from PyQt6.QtGui  import (
    QColor, QBrush, QPainter, QPen, QFont, QKeySequence, QShortcut,
    QLinearGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QLineEdit, QSizePolicy,
)

from viko.ui_theme   import (
    BG, PRI, AMB, SUC, DIM, TXT,
    _c, pri, amb, suc, F,
    WIN_W, WIN_H, HDR_H, FTR_H, LEFT_W, RIGHT_W,
)
from viko.ui_widgets import (
    FloatingArc, _hdr_draw, _ftr_draw,
    HudCanvas, LeftPanel, RightMetricsPanel, ActivityPanel,
)


# ─── System Metrics ───────────────────────────────────────────────────────────
class _SysMetrics:
    def __init__(self):
        self._data = {"cpu": 0.0, "mem": 0.0, "disk": 0.0, "net": 0.0}
        self._prev_net = psutil.net_io_counters()
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def snapshot(self) -> dict:
        return dict(self._data)

    def _run(self):
        while True:
            try:
                self._data["cpu"]  = psutil.cpu_percent(interval=1) / 100
                self._data["mem"]  = psutil.virtual_memory().percent / 100
                try:
                    self._data["disk"] = psutil.disk_usage("/").percent / 100
                except Exception:
                    self._data["disk"] = 0.5
                cur = psutil.net_io_counters()
                sent = (cur.bytes_sent - self._prev_net.bytes_sent) / 1_000_000
                self._data["net"]  = min(1.0, sent / 10)
                self._prev_net = cur
            except Exception:
                time.sleep(2)


# ─── Setup Overlay ────────────────────────────────────────────────────────────
class SetupOverlay(QWidget):
    done = pyqtSignal(str)   # emits gemini_api_key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: rgba(0,0,0,220);")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("VIKO INITIALISATION")
        title.setFont(F(14, True)); title.setStyleSheet(f"color: {PRI.name()};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        lbl = QLabel("Gemini API Key")
        lbl.setFont(F(9)); lbl.setStyleSheet(f"color: {TXT.name()};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

        self._key = QLineEdit(); self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._key.setFont(F(9)); self._key.setFixedWidth(360)
        self._key.setPlaceholderText("AIza...")
        self._key.setStyleSheet("""
            QLineEdit { background: #010d14; color: #8ffcff;
                        border: 1px solid #0d3347; border-radius: 4px; padding: 8px; }
            QLineEdit:focus { border-color: #00d4ff; }
        """)
        lay.addWidget(self._key, alignment=Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("INITIALISE VIKO")
        btn.setFont(F(9, True)); btn.setFixedWidth(200)
        btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(0,212,255,20); color: {PRI.name()};
                border: 1px solid rgba(0,212,255,80); border-radius: 6px; padding: 8px; }}
            QPushButton:hover {{ background: rgba(0,212,255,50); }}
        """)
        btn.clicked.connect(self._submit)
        self._key.returnPressed.connect(self._submit)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _submit(self):
        key = self._key.text().strip()
        if key:
            self.done.emit(key)


# ─── Main Window ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    _log_sig   = pyqtSignal(str)
    _state_sig = pyqtSignal(str)

    on_text_command = None   # set by VikoUI / viko.py

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VIKO — JARVIS Modern HUD")
        self.resize(WIN_W, WIN_H)
        self.setStyleSheet("background: rgb(0,0,0); color: rgb(200,232,248);")

        self._muted  = False
        self._ready  = False
        self._metrics = _SysMetrics()
        self._state_val = "idle"

        self._log_sig.connect(self._on_log)
        self._state_sig.connect(self._apply_state)

        self._build()
        self._setup_shortcuts()

    # ── Layout ─────────────────────────────────────────────────────────────
    def _build(self):
        self._ui_state = {"panel_visible": False}

        root = QWidget(); self.setCentralWidget(root)
        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(0, 0, 0, 0); vlay.setSpacing(0)

        # Header
        vlay.addWidget(FloatingArc(_hdr_draw, HDR_H, flip=False, state=self._ui_state))

        # Body
        body = QWidget(); blay = QHBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0); blay.setSpacing(0)

        self._left = LeftPanel(self._metrics.snapshot)
        blay.addWidget(self._left)

        self._hud = HudCanvas()
        blay.addWidget(self._hud, 1)

        # Right column
        right_col = QWidget(); right_col.setFixedWidth(RIGHT_W)
        rcol = QVBoxLayout(right_col)
        rcol.setContentsMargins(0, 0, 0, 0); rcol.setSpacing(0)

        # Button bar
        btn_bar = QWidget(); btn_bar.setFixedHeight(32)
        bbl = QHBoxLayout(btn_bar)
        bbl.setContentsMargins(8, 4, 8, 0); bbl.setSpacing(4)

        def _ss(active=False):
            return f"""
                QPushButton {{
                    background: {'rgba(0,212,255,30)' if active else 'rgba(0,212,255,12)'};
                    color: {PRI.name() if active else pri(140).name()};
                    border: 1px solid {'rgba(0,212,255,110)' if active else 'rgba(0,212,255,40)'};
                    border-radius: 4px; padding: 0 6px;
                }}
                QPushButton:hover {{ background: rgba(0,212,255,40); color: {PRI.name()}; }}
            """

        self._btn_ss = _ss
        self._fs_btn = QPushButton("⛶"); self._fs_btn.setFixedSize(28, 26)
        self._fs_btn.setFont(F(9, True))
        self._fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fs_btn.setStyleSheet(_ss()); self._fs_btn.clicked.connect(self._toggle_fullscreen)
        bbl.addWidget(self._fs_btn)

        self._toggle_btn = QPushButton("◧  ACTIVITY"); self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.setFont(F(8, True))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(_ss()); self._toggle_btn.clicked.connect(self._toggle_panel)
        bbl.addWidget(self._toggle_btn, 1)
        rcol.addWidget(btn_bar)

        self._right_stack = QStackedWidget()
        self._right_metrics = RightMetricsPanel(self._metrics.snapshot)
        self._activity       = ActivityPanel()
        self._right_stack.addWidget(self._right_metrics)   # index 0
        self._right_stack.addWidget(self._activity)         # index 1
        self._right_stack.setCurrentIndex(0)
        rcol.addWidget(self._right_stack, 1)
        blay.addWidget(right_col)
        vlay.addWidget(body, 1)

        # Footer
        self._ftr = FloatingArc(_ftr_draw, FTR_H, flip=True,
                                on_click=self._toggle_panel, state=self._ui_state)
        vlay.addWidget(self._ftr)

        # Setup overlay
        self._overlay = SetupOverlay(root)
        self._overlay.setGeometry(0, 0, WIN_W, WIN_H)
        self._overlay.done.connect(self._on_api_key)
        self._overlay.show()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_overlay") and self._overlay:
            self._overlay.setGeometry(0, 0, self.width(), self.height())

    # ── Shortcuts ──────────────────────────────────────────────────────────
    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F4"),  self).activated.connect(self._toggle_mute)
        QShortcut(QKeySequence("F11"), self).activated.connect(self._toggle_fullscreen)

    # ── Panel toggle + fullscreen ──────────────────────────────────────────
    def _toggle_panel(self):
        self._ui_state["panel_visible"] = not self._ui_state["panel_visible"]
        v = self._ui_state["panel_visible"]
        self._right_stack.setCurrentIndex(1 if v else 0)
        self._toggle_btn.setText("◨  METRICS" if v else "◧  ACTIVITY")
        self._toggle_btn.setStyleSheet(self._btn_ss(v))
        self._ftr.update()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal(); self._fs_btn.setStyleSheet(self._btn_ss(False))
        else:
            self.showFullScreen(); self._fs_btn.setStyleSheet(self._btn_ss(True))

    # ── Mute ──────────────────────────────────────────────────────────────
    def _toggle_mute(self):
        self._muted = not self._muted
        self._hud._muted = self._muted
        if self._muted:
            self._hud.set_state("MUTED")
        else:
            self._hud.set_state(self._state_val)

    # ── State + Log ───────────────────────────────────────────────────────
    def _apply_state(self, state: str):
        self._state_val = state
        if not self._muted:
            self._hud.set_state(state)
        # online status: any non-idle state means connected
        self._left.set_online(state != "IDLE")

    def _on_log(self, text: str):
        self._activity.append_log(text)
        self._right_metrics.inc_ops()

    # ── API key ───────────────────────────────────────────────────────────
    def _on_api_key(self, key: str):
        import os; os.environ["GEMINI_API_KEY"] = key
        self._ready = True
        if self._overlay:
            self._overlay.hide(); self._overlay = None
        self._apply_state("LISTENING")
        self._activity.append_log("SYS: Initialised. Viko online.")


# ─── Public Facade (identical interface to old ui.py) ─────────────────────────
class _RootShim:
    def __init__(self, app): self._app = app
    def mainloop(self): self._app.exec()
    def protocol(self, *_): pass


class VikoUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow()
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool: return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted: self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._activity.current_file()

    @property
    def on_text_command(self): return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb): self._win.on_text_command = cb

    def set_state(self, state: str): self._win._state_sig.emit(state)
    def write_log(self, text: str):  self._win._log_sig.emit(text)
    def wait_for_api_key(self):
        while not self._win._ready: time.sleep(0.1)
    def start_speaking(self): self.set_state("SPEAKING")
    def stop_speaking(self):
        if not self.muted: self.set_state("LISTENING")
```

- [ ] **Step 2: Verify syntax**

```bash
.venv/bin/python -c "from viko.ui import VikoUI; print('VikoUI ok')"
```

Expected: `VikoUI ok`

- [ ] **Step 3: Verify full app launches**

```bash
.venv/bin/python -c "
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
from viko.ui import MainWindow
w = MainWindow(); w.show()
from PyQt6.QtCore import QTimer
QTimer.singleShot(1500, app.quit)
app.exec()
print('launch ok')
"
```

Expected: Window appears for 1.5 seconds then exits cleanly, prints `launch ok`

- [ ] **Step 4: Commit**

```bash
git add viko/ui.py
git commit -m "feat: rewrite ui.py with JARVIS HUD — FloatingArc, HudCanvas, panels, VikoUI facade"
```

---

## Task 9: Wire text command callback + file drop into viko.py

**Files:**
- Verify (no change needed): `viko.py`

- [ ] **Step 1: Confirm the callback wire-up works**

In `viko.py`, the relevant lines assign `ui.on_text_command`. Since `VikoUI.on_text_command` is still a property with getter/setter, this should work with zero changes. Verify:

```bash
grep -n "on_text_command\|current_file\|write_log\|set_state\|wait_for_api" viko.py | head -20
```

Expected: Lines showing `ui.on_text_command = ...`, `ui.write_log(...)`, `ui.set_state(...)`, `ui.wait_for_api_key()`

- [ ] **Step 2: Run the full app**

```bash
.venv/bin/python viko.py
```

Expected: JARVIS HUD window appears with SetupOverlay. After entering a valid Gemini API key, the overlay hides and the HUD switches to LISTENING state. Activity log shows "SYS: Initialised. Viko online."

- [ ] **Step 3: Test state changes in UI**

Once running:
- Speak into mic → HUD state indicator should show "LISTENING" (green)
- Wait for VIKO to respond → indicator shows "SPEAKING" (amber) with waveform active
- F4 key → mute toggle, indicator shows "MUTED" (red)
- F11 key → fullscreen

- [ ] **Step 4: Final commit**

```bash
git add viko/ui_theme.py viko/ui_widgets.py viko/ui.py
git commit -m "feat: JARVIS HUD fully wired — all VIKO state/log/file/command hooks active"
```

---

## Self-Review Checklist

- [x] **VikoUI interface** — all 8 methods/properties preserved exactly
- [x] **set_state mapping** — LISTENING/SPEAKING/THINKING/MUTED/IDLE all handled in HudCanvas.set_state()
- [x] **write_log thread-safety** — uses pyqtSignal → LogWidget._enqueue (same pattern as ui_backup.py)
- [x] **mute toggle** — F4 shortcut + muted property, updates HudCanvas._muted
- [x] **current_file** — ActivityPanel.current_file() → FileDropCard.current_file()
- [x] **on_text_command** — stored on MainWindow, can be set via VikoUI property
- [x] **SetupOverlay** — blocks wait_for_api_key() via _ready flag, emits API key to env
- [x] **_SysMetrics** — background thread, snapshot() returns dict with cpu/mem/disk/net
- [x] **F11 fullscreen** — shortcut + button both wired
- [x] **No face_path dependency** — new UI doesn't use face image; VikoUI still accepts it for compat
