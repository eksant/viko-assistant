"""
Embedded Chromium browser panel for VIKO.
Uses QWebEngineView (PyQt6-WebEngine).
CDP remote debugging port set via QTWEBENGINE_CHROMIUM_FLAGS env var (done in ui.py).
"""
from __future__ import annotations
import os

from PyQt6.QtCore    import Qt, QUrl, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui     import QAction, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QSplitter, QMenu, QStackedWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore    import QWebEnginePage

from viko.ui_theme import PRI, AMB, F

CDP_PORT = int(os.environ.get("VIKO_CDP_PORT", "9222"))

_NAV_STYLE = """
    QPushButton {
        background: rgba(0,212,255,18);
        color: rgba(200,232,248,220);
        border: 1px solid rgba(0,212,255,50);
        border-radius: 4px;
        font-size: 14px;
    }
    QPushButton:hover { background: rgba(0,212,255,45); color: #ffffff; }
    QPushButton:pressed { background: rgba(0,212,255,70); }
    QPushButton:disabled { color: rgba(200,232,248,60); border-color: rgba(0,212,255,20); }
"""

_MINIMIZE_STYLE = f"""
    QPushButton {{
        background: rgba(0,212,255,25);
        color: {PRI.name()};
        border: 1px solid rgba(0,212,255,80);
        border-radius: 4px;
        font-size: 10px;
        font-weight: bold;
        padding: 0 8px;
    }}
    QPushButton:hover {{ background: rgba(0,212,255,55); color: #ffffff; }}
"""

_DEVTOOLS_STYLE = f"""
    QPushButton {{
        background: rgba(0,212,255,18);
        color: rgba(200,232,248,220);
        border: 1px solid rgba(0,212,255,50);
        border-radius: 4px;
    }}
    QPushButton:hover {{ background: rgba(0,212,255,45); color: #ffffff; }}
    QPushButton:checked {{
        background: rgba(255,179,71,30);
        color: {AMB.name()};
        border-color: rgba(255,179,71,100);
    }}
"""

_MENU_STYLE = f"""
    QMenu {{
        background: #010d14;
        border: 1px solid rgba(0,212,255,70);
        border-radius: 6px;
        color: rgba(200,232,248,220);
        padding: 4px 0;
    }}
    QMenu::item {{
        padding: 7px 22px 7px 14px;
        font-size: 11px;
        font-family: 'Courier New';
    }}
    QMenu::item:selected {{
        background: rgba(0,212,255,28);
        color: {PRI.name()};
    }}
    QMenu::item:disabled {{
        color: rgba(200,232,248,60);
    }}
    QMenu::separator {{
        height: 1px;
        background: rgba(0,212,255,25);
        margin: 3px 8px;
    }}
"""


class BrowserPanel(QWidget):
    page_loaded        = pyqtSignal(str)   # emits url on navigation
    title_changed      = pyqtSignal(str)   # emits page title
    minimize_requested = pyqtSignal()      # user clicked ◀ VIKO

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devtools_visible = False
        self._zoom_factor = 1.0
        self._headless = False
        self._setup_ui()
        self._connect_signals()
        # Periodic screenshot refresh when headless (every 2s)
        self._headless_timer = QTimer(self)
        self._headless_timer.setInterval(2000)
        self._headless_timer.timeout.connect(self._refresh_headless_screenshot)

    # ── UI ────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # URL bar
        bar = QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet(
            "background: #010d14;"
            "border-bottom: 1px solid rgba(0,212,255,40);"
        )
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(8, 4, 8, 4)
        bl.setSpacing(5)

        # ◀ VIKO — minimize back to HUD
        self._min_btn = QPushButton("◀  VIKO")
        self._min_btn.setFixedSize(72, 28)
        self._min_btn.setFont(F(8, True))
        self._min_btn.setToolTip("Minimize browser — back to HUD")
        self._min_btn.setStyleSheet(_MINIMIZE_STYLE)
        bl.addWidget(self._min_btn)

        sep = QLabel("│")
        sep.setStyleSheet("color: rgba(0,212,255,40); font-size: 16px;")
        bl.addWidget(sep)

        # Nav buttons
        def _nav(label: str, tip: str, size: int = 28) -> QPushButton:
            b = QPushButton(label)
            b.setFixedSize(size, 28)
            b.setToolTip(tip)
            b.setStyleSheet(_NAV_STYLE)
            return b

        self._back_btn   = _nav("‹", "Back (Alt+←)")
        self._fwd_btn    = _nav("›", "Forward (Alt+→)")
        self._reload_btn = _nav("⟳", "Reload (F5)")
        self._home_btn   = _nav("⌂", "Workspace home")
        for b in (self._back_btn, self._fwd_btn, self._reload_btn, self._home_btn):
            bl.addWidget(b)

        # URL bar input
        self._url_bar = QLineEdit()
        self._url_bar.setFont(F(9))
        self._url_bar.setPlaceholderText("https://  or  file://  or  type to search")
        self._url_bar.setStyleSheet("""
            QLineEdit {
                background: rgba(0,12,24,220);
                color: rgba(200,232,248,240);
                border: 1px solid rgba(0,212,255,60);
                border-radius: 5px;
                padding: 3px 10px;
                selection-background-color: rgba(0,212,255,60);
            }
            QLineEdit:focus {
                border-color: rgba(0,212,255,160);
                color: #ffffff;
            }
        """)
        bl.addWidget(self._url_bar, 1)

        # LOCAL / WEB badge
        self._mode_badge = QLabel("WEB")
        self._mode_badge.setFont(F(7, True))
        self._mode_badge.setFixedWidth(42)
        self._mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode_badge.setStyleSheet(
            f"color: {PRI.name()}; background: rgba(0,212,255,18);"
            f"border: 1px solid rgba(0,212,255,50); border-radius: 3px; padding: 2px;"
        )
        bl.addWidget(self._mode_badge)

        # DevTools toggle
        self._devtools_btn = QPushButton("⚙")
        self._devtools_btn.setFixedSize(28, 28)
        self._devtools_btn.setToolTip("Toggle DevTools")
        self._devtools_btn.setCheckable(True)
        self._devtools_btn.setStyleSheet(_DEVTOOLS_STYLE)
        bl.addWidget(self._devtools_btn)

        # Settings menu button
        self._settings_btn = QPushButton("☰")
        self._settings_btn.setFixedSize(28, 28)
        self._settings_btn.setToolTip("Browser settings")
        self._settings_btn.setStyleSheet(_NAV_STYLE)
        bl.addWidget(self._settings_btn)

        root.addWidget(bar)

        # Splitter: web view + devtools
        self._splitter = QSplitter(Qt.Orientation.Vertical)

        self._web_view = QWebEngineView()
        self._web_view.setStyleSheet("background: #000;")
        self._splitter.addWidget(self._web_view)

        self._devtools_view = QWebEngineView()
        self._devtools_view.setVisible(False)
        self._splitter.addWidget(self._devtools_view)
        self._splitter.setSizes([700, 0])

        self._web_view.page().setDevToolsPage(self._devtools_view.page())

        # Headless pane: screenshot grab + "AI control" overlay
        self._headless_widget = QWidget()
        self._headless_widget.setStyleSheet("background: #000;")
        hl = QVBoxLayout(self._headless_widget)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self._headless_shot = QLabel()
        self._headless_shot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._headless_shot.setStyleSheet("background: #000;")
        hl.addWidget(self._headless_shot, 1)

        self._headless_banner = QLabel("◈  HEADLESS MODE  —  AI is in control")
        self._headless_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._headless_banner.setFont(F(9, True))
        self._headless_banner.setFixedHeight(26)
        self._headless_banner.setStyleSheet(
            f"color: {PRI.name()}; background: rgba(0,212,255,18);"
            f"border-top: 1px solid rgba(0,212,255,50); letter-spacing: 1px;"
        )
        hl.addWidget(self._headless_banner)

        # Stack: index 0 = live view, index 1 = headless screenshot
        self._view_stack = QStackedWidget()
        self._view_stack.addWidget(self._splitter)       # 0 – live
        self._view_stack.addWidget(self._headless_widget) # 1 – headless
        self._view_stack.setCurrentIndex(0)

        root.addWidget(self._view_stack, 1)

    def _connect_signals(self):
        # Use lambdas to absorb the bool arg emitted by clicked signal
        self._min_btn.clicked.connect(lambda _=False: self.minimize_requested.emit())
        self._back_btn.clicked.connect(lambda _=False: self._web_view.back())
        self._fwd_btn.clicked.connect(lambda _=False: self._web_view.forward())
        self._reload_btn.clicked.connect(lambda _=False: self._web_view.reload())
        self._home_btn.clicked.connect(self._go_home)
        self._url_bar.returnPressed.connect(self._on_url_entered)
        self._devtools_btn.toggled.connect(self._toggle_devtools)
        self._settings_btn.clicked.connect(self._show_settings_menu)

        self._web_view.urlChanged.connect(self._on_url_changed)
        self._web_view.titleChanged.connect(self.title_changed)
        self._web_view.loadFinished.connect(self._on_load_finished)
        self._web_view.loadStarted.connect(self._on_load_started)

    # ── Public API ────────────────────────────────────────────────────────
    def navigate(self, url: str) -> None:
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url
        self._web_view.load(QUrl(url))
        self._update_badge(url)

    def current_url(self) -> str:
        return self._web_view.url().toString()

    def page(self) -> QWebEnginePage:
        return self._web_view.page()

    # ── Slots ─────────────────────────────────────────────────────────────
    def _go_home(self):
        from viko.workspace import WORKSPACE
        self.navigate((WORKSPACE / "documents").as_uri())

    def _on_url_entered(self):
        text = self._url_bar.text().strip()
        if not text:
            return
        if text.startswith(("http://", "https://", "file://")):
            self.navigate(text)
        elif "." in text and " " not in text:
            self.navigate("https://" + text)
        else:
            self.navigate(f"https://www.google.com/search?q={text.replace(' ', '+')}")

    def _on_url_changed(self, qurl: QUrl):
        url = qurl.toString()
        self._url_bar.setText(url)
        self._update_badge(url)
        self.page_loaded.emit(url)

    def _on_load_started(self):
        self._reload_btn.setText("✕")
        self._reload_btn.setToolTip("Stop loading")
        self._reload_btn.clicked.disconnect()
        self._reload_btn.clicked.connect(lambda _=False: self._web_view.stop())

    def _on_load_finished(self, _ok: bool):
        self._reload_btn.setText("⟳")
        self._reload_btn.setToolTip("Reload (F5)")
        self._reload_btn.clicked.disconnect()
        self._reload_btn.clicked.connect(lambda _=False: self._web_view.reload())

        hist = self._web_view.history()
        self._back_btn.setEnabled(hist.canGoBack())
        self._fwd_btn.setEnabled(hist.canGoForward())
        if self._headless:
            self._refresh_headless_screenshot()

    def _toggle_devtools(self, checked: bool):
        self._devtools_view.setVisible(checked)
        self._splitter.setSizes([600, 300] if checked else [1, 0])

    # ── Headless mode ─────────────────────────────────────────────────────
    @property
    def headless_mode(self) -> bool:
        return self._headless

    @headless_mode.setter
    def headless_mode(self, enabled: bool):
        if self._headless == enabled:
            return
        self._headless = enabled
        if enabled:
            self._refresh_headless_screenshot()
            self._view_stack.setCurrentIndex(1)
            self._headless_timer.start()
            self._mode_badge.setText("HDLS")
            self._mode_badge.setStyleSheet(
                f"color: {PRI.name()}; background: rgba(0,212,255,30);"
                f"border: 1px solid {PRI.name()}; border-radius: 3px; padding: 2px;"
            )
        else:
            self._headless_timer.stop()
            self._view_stack.setCurrentIndex(0)
            self._update_badge(self.current_url())

    def _refresh_headless_screenshot(self):
        px = self._web_view.grab()
        if px.isNull():
            return
        target = self._headless_shot.size()
        if target.isEmpty():
            return
        scaled = px.scaled(target, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        self._headless_shot.setPixmap(scaled)

    def _update_badge(self, url: str):
        if url.startswith("file://"):
            self._mode_badge.setText("LOCAL")
            self._mode_badge.setStyleSheet(
                f"color: {AMB.name()}; background: rgba(255,179,71,18);"
                f"border: 1px solid rgba(255,179,71,70); border-radius: 3px; padding: 2px;"
            )
        else:
            self._mode_badge.setText("WEB")
            self._mode_badge.setStyleSheet(
                f"color: {PRI.name()}; background: rgba(0,212,255,18);"
                f"border: 1px solid rgba(0,212,255,50); border-radius: 3px; padding: 2px;"
            )

    # ── Settings menu ─────────────────────────────────────────────────────
    def _show_settings_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_STYLE)

        pct = int(self._web_view.zoomFactor() * 100)

        zoom_out = QAction("🔎  Zoom Out", self)
        zoom_out.triggered.connect(lambda: self._set_zoom(self._web_view.zoomFactor() - 0.1))
        menu.addAction(zoom_out)

        zoom_reset = QAction(f"⊙   Reset Zoom  ({pct}%)", self)
        zoom_reset.triggered.connect(lambda: self._set_zoom(1.0))
        menu.addAction(zoom_reset)

        zoom_in = QAction("🔍  Zoom In", self)
        zoom_in.triggered.connect(lambda: self._set_zoom(self._web_view.zoomFactor() + 0.1))
        menu.addAction(zoom_in)

        menu.addSeparator()

        copy_url = QAction("📋  Copy URL", self)
        copy_url.triggered.connect(self._copy_url)
        menu.addAction(copy_url)

        open_ext = QAction("🌐  Open in External Browser", self)
        open_ext.triggered.connect(self._open_external)
        menu.addAction(open_ext)

        menu.addSeparator()

        js_enabled = self._web_view.page().settings().testAttribute(
            self._web_view.page().settings().WebAttribute.JavascriptEnabled
        )
        toggle_js = QAction(f"{'✅' if js_enabled else '☐'}  JavaScript", self)
        toggle_js.triggered.connect(lambda: self._toggle_js(not js_enabled))
        menu.addAction(toggle_js)

        menu.addSeparator()

        clear_hist = QAction("⌫   Clear History", self)
        clear_hist.triggered.connect(lambda: self._web_view.history().clear())
        menu.addAction(clear_hist)

        clear_cache = QAction("🗑   Clear Cache", self)
        clear_cache.triggered.connect(self._clear_cache)
        menu.addAction(clear_cache)

        pos = self._settings_btn.mapToGlobal(QPoint(0, self._settings_btn.height()))
        menu.exec(pos)

    def _set_zoom(self, factor: float):
        self._web_view.setZoomFactor(max(0.25, min(5.0, round(factor, 1))))

    def _copy_url(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.current_url())

    def _open_external(self):
        QDesktopServices.openUrl(QUrl(self.current_url()))

    def _clear_cache(self):
        profile = self._web_view.page().profile()
        profile.clearHttpCache()
        profile.clearAllVisitedLinks()

    def _toggle_js(self, enabled: bool):
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        self._web_view.page().settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, enabled
        )
        self._web_view.reload()
