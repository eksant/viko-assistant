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
from viko.config import is_configured, get_gemini_key


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

        # Setup overlay — skip if key already in .env
        if is_configured():
            self._overlay = None
            self._ready = True
            import os
            os.environ.setdefault("GEMINI_API_KEY", get_gemini_key())
            QTimer.singleShot(200, lambda: self._apply_state("LISTENING"))
            QTimer.singleShot(250, lambda: self._activity.append_log("SYS: Viko online."))
        else:
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
