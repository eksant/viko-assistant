# viko/ui.py
from __future__ import annotations
import math, sys, time, threading, socket
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
    QDialog,
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
        self._data     = {"cpu": 0.0, "mem": 0.0, "disk": 0.0, "net": 0.0, "latency": 0}
        self._prev_net = psutil.net_io_counters()
        self._ping_ctr = 0
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def snapshot(self) -> dict:
        return dict(self._data)

    def _measure_latency(self) -> int:
        try:
            t0 = time.perf_counter()
            s  = socket.create_connection(("8.8.8.8", 53), timeout=3)
            s.close()
            return max(1, int((time.perf_counter() - t0) * 1000))
        except Exception:
            return self._data["latency"] or 999

    def _run(self):
        while True:
            try:
                self._data["cpu"]  = psutil.cpu_percent(interval=1) / 100
                self._data["mem"]  = psutil.virtual_memory().percent / 100
                try:
                    self._data["disk"] = psutil.disk_usage("/").percent / 100
                except Exception:
                    self._data["disk"] = 0.5
                cur  = psutil.net_io_counters()
                sent = (cur.bytes_sent - self._prev_net.bytes_sent) / 1_000_000
                self._data["net"]  = min(1.0, sent / 10)
                self._prev_net = cur
                self._ping_ctr += 1
                if self._ping_ctr % 15 == 1:   # measure every ~15s
                    self._data["latency"] = self._measure_latency()
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
    _loc_sig   = pyqtSignal(float, float, str)   # lat, lon, label

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
        self._loc_sig.connect(self._on_location)

        self._build()
        self._setup_shortcuts()
        self._start_live_feeds()

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

        self._toggle_btn = QPushButton("◧  ACTIVITY"); self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.setFont(F(8, True))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(_ss()); self._toggle_btn.clicked.connect(self._toggle_panel)
        bbl.addWidget(self._toggle_btn, 1)

        self._fs_btn = QPushButton("⛶"); self._fs_btn.setFixedSize(28, 26)
        self._fs_btn.setFont(F(10, True))
        self._fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fs_btn.setStyleSheet(_ss()); self._fs_btn.clicked.connect(self._toggle_fullscreen)
        bbl.addWidget(self._fs_btn)

        self._rst_btn = QPushButton("⟳ RST"); self._rst_btn.setFixedHeight(26)
        self._rst_btn.setFixedWidth(52)
        self._rst_btn.setFont(F(8, True))
        self._rst_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rst_btn.setToolTip("Restart VIKO")
        self._rst_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,179,71,15);
                color: {AMB.name()};
                border: 1px solid rgba(255,179,71,60);
                border-radius: 4px; padding: 0 4px;
            }}
            QPushButton:hover {{ background: rgba(255,179,71,40); color: {AMB.name()}; }}
        """)
        self._rst_btn.clicked.connect(self._restart)
        bbl.addWidget(self._rst_btn)

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

    def _restart(self):
        dlg = QDialog(self, Qt.WindowType.FramelessWindowHint)
        dlg.setFixedSize(300, 130)
        dlg.setStyleSheet("""
            QDialog {
                background: #010d14;
                border: 1px solid rgba(255,179,71,120);
                border-radius: 8px;
            }
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 18, 20, 14); lay.setSpacing(10)

        title = QLabel("⟳  RESTART VIKO")
        title.setFont(F(11, True))
        title.setStyleSheet(f"color: {AMB.name()}; background: transparent;")
        lay.addWidget(title)

        msg = QLabel("Restart aplikasi sekarang?")
        msg.setFont(F(9))
        msg.setStyleSheet(f"color: {TXT.name()}; background: transparent;")
        lay.addWidget(msg)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        _btn_style = lambda c, a: f"""
            QPushButton {{
                background: rgba({c},15); color: rgba({c},220);
                border: 1px solid rgba({c},80); border-radius: 4px;
                padding: 5px 0;
            }}
            QPushButton:hover {{ background: rgba({c},{a}); }}
        """
        yes = QPushButton("Ya, Restart"); yes.setFont(F(9, True))
        yes.setStyleSheet(_btn_style("255,179,71", 50))
        no  = QPushButton("Batal"); no.setFont(F(9))
        no.setStyleSheet(_btn_style("0,212,255", 40))

        yes.clicked.connect(dlg.accept)
        no.clicked.connect(dlg.reject)
        btn_row.addWidget(no); btn_row.addWidget(yes)
        lay.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            import os
            QApplication.instance().quit()
            os.execv(sys.executable, [sys.executable] + sys.argv)

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

    # ── Live data feeds ───────────────────────────────────────────────────
    def _start_live_feeds(self):
        # Latency: poll metrics snapshot every 5s and push to CommsCard
        lat_timer = QTimer(self)
        lat_timer.timeout.connect(self._push_latency)
        lat_timer.start(5000)

        # Location: fetch once from IP geolocation in background
        t = threading.Thread(target=self._fetch_location, daemon=True)
        t.start()

    def _push_latency(self):
        ms = self._metrics.snapshot().get("latency", 0)
        if ms > 0:
            self._right_metrics.set_latency(ms)

    def _fetch_location(self):
        try:
            import urllib.request, json as _json
            with urllib.request.urlopen("http://ip-api.com/json/", timeout=6) as r:
                d = _json.loads(r.read())
            lat   = float(d.get("lat", 3.14))
            lon   = float(d.get("lon", 101.69))
            city  = d.get("city", "")
            country = d.get("countryCode", "")
            # Format as degree-minute label
            la_d, la_m = int(abs(lat)), int((abs(lat) % 1) * 60)
            lo_d, lo_m = int(abs(lon)), int((abs(lon) % 1) * 60)
            la_s = f"{la_d:02d}°{la_m:02d}′{'N' if lat >= 0 else 'S'}"
            lo_s = f"{lo_d:03d}°{lo_m:02d}′{'E' if lon >= 0 else 'W'}"
            label = f"{la_s}  {lo_s}"
            self._loc_sig.emit(lat, lon, label)
        except Exception:
            pass   # keep default KL coordinates

    def _on_location(self, lat: float, lon: float, label: str):
        self._left.set_location(lat, lon, label)


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
