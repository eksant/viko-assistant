# VIKO Embedded Browser + AI Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed a fully interactive Chromium browser inside the VIKO window (replacing center HUD when active), with AI tools to render generated files, control the browser, and integrate agent-browser for AI-visual interaction.

**Architecture:** `QWebEngineView` (PyQt6-WebEngine) embeds real Chromium in the center panel; a `QStackedWidget` switches between HUD (index 0) and BrowserPanel (index 1). A `workspace/` folder holds AI-generated HTML files rendered locally. Playwright connects to the embedded browser via CDP on port 9222; agent-browser runs as a Node.js subprocess for screenshot-based AI interaction.

**Tech Stack:** PyQt6-WebEngine (QWebEngineView), Playwright (Python), agent-browser (Node.js/npx), Python sqlite3, QSplitter for DevTools split panel.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `viko/browser_panel.py` | **Create** | BrowserPanel widget: QWebEngineView + URL bar + DevTools split |
| `viko/workspace.py` | **Create** | Workspace folder manager + HTML/presentation/wireframe templates |
| `viko/agent_browser.py` | **Create** | agent-browser Node.js subprocess wrapper |
| `viko/skills/browser_tool.py` | **Create** | AI skill: navigate, render_content, screenshot, get_page_content |
| `viko/ui.py` | **Modify** | Add 🌐 button, center QStackedWidget, toggle_browser(), set_browser_url() |
| `viko.py` | **Modify** | Add 4 tool declarations + handlers in _execute_tool() |
| `requirements.txt` | **Modify** | Add PyQt6-WebEngine |
| `workspace/` | **Create** | wireframes/ presentations/ documents/ code/ with .gitkeep |

---

## Task 1: Workspace folder structure + viko/workspace.py

**Files:**
- Create: `workspace/wireframes/.gitkeep`
- Create: `workspace/presentations/.gitkeep`
- Create: `workspace/documents/.gitkeep`
- Create: `workspace/code/.gitkeep`
- Create: `viko/workspace.py`

- [ ] **Step 1: Create workspace folder structure**

```bash
mkdir -p /Users/eksa/Projects/viko-assistant/workspace/wireframes
mkdir -p /Users/eksa/Projects/viko-assistant/workspace/presentations
mkdir -p /Users/eksa/Projects/viko-assistant/workspace/documents
mkdir -p /Users/eksa/Projects/viko-assistant/workspace/code
touch workspace/wireframes/.gitkeep workspace/presentations/.gitkeep workspace/documents/.gitkeep workspace/code/.gitkeep
```

- [ ] **Step 2: Create viko/workspace.py**

```python
# viko/workspace.py
from __future__ import annotations
import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


WORKSPACE = _base_dir() / "workspace"
_CATEGORIES = ("wireframes", "presentations", "documents", "code")


def ensure_dirs() -> None:
    for cat in _CATEGORIES:
        (WORKSPACE / cat).mkdir(parents=True, exist_ok=True)


def save_file(content: str, filename: str, category: str = "documents") -> Path:
    if category not in _CATEGORIES:
        category = "documents"
    ensure_dirs()
    path = WORKSPACE / category / filename
    path.write_text(content, encoding="utf-8")
    return path


def file_url(path: Path) -> str:
    return path.as_uri()


def list_files(category: str) -> list[dict]:
    ensure_dirs()
    folder = WORKSPACE / category
    result = []
    for f in sorted(folder.iterdir()):
        if f.name.startswith("."):
            continue
        result.append({
            "name": f.name,
            "path": str(f),
            "url":  file_url(f),
            "size": f.stat().st_size,
        })
    return result


def html_template(title: str, body_html: str, styles: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #000;
    color: #c8e8f8;
    font-family: 'Courier New', monospace;
    padding: 24px;
    min-height: 100vh;
  }}
  h1, h2, h3 {{ color: #00d4ff; margin-bottom: 12px; }}
  a {{ color: #00d4ff; }}
  hr {{ border-color: rgba(0,212,255,0.2); margin: 16px 0; }}
  {styles}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


def wireframe_template(title: str, components: list[dict]) -> str:
    """
    components: list of dicts with keys: type, label, x, y, w, h
    type: 'box' | 'text' | 'button' | 'input' | 'image'
    """
    boxes = ""
    for c in components:
        x, y = c.get("x", 0), c.get("y", 0)
        w, h = c.get("w", 120), c.get("h", 40)
        lbl  = c.get("label", "")
        kind = c.get("type", "box")
        color_map = {
            "button": "#00d4ff",
            "input":  "#ffb347",
            "image":  "#555",
            "text":   "transparent",
            "box":    "rgba(0,212,255,0.08)",
        }
        bg = color_map.get(kind, "rgba(0,212,255,0.08)")
        boxes += (
            f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
            f'border:1px solid rgba(0,212,255,0.5);background:{bg};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:11px;color:#c8e8f8;border-radius:3px;">'
            f'{lbl}</div>'
        )
    body = f'<h2 style="margin-bottom:16px">{title}</h2><div style="position:relative;height:700px">{boxes}</div>'
    return html_template(title, body)


def presentation_template(title: str, slides: list[dict]) -> str:
    """
    slides: list of dicts with keys: title (str), content (str, HTML ok), notes (str optional)
    """
    slides_html = ""
    for slide in slides:
        notes_html = f'<aside class="notes">{slide.get("notes","")}</aside>' if slide.get("notes") else ""
        slides_html += f"""
        <section>
          <h2>{slide.get("title","")}</h2>
          <div class="content">{slide.get("content","")}</div>
          {notes_html}
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/black.css">
<style>
  .reveal {{ font-family: 'Courier New', monospace; }}
  .reveal h2 {{ color: #00d4ff; text-transform: none; }}
  .reveal .content {{ font-size: 0.85em; line-height: 1.6; }}
  .reveal section {{ text-align: left; padding: 0 40px; }}
</style>
</head>
<body>
<div class="reveal">
  <div class="slides">{slides_html}
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
<script>Reveal.initialize({{ hash: true, transition: 'fade' }});</script>
</body>
</html>"""
```

- [ ] **Step 3: Smoke-test workspace.py**

```bash
.venv/bin/python -c "
from viko.workspace import save_file, file_url, list_files, html_template, wireframe_template, presentation_template
p = save_file(html_template('Test', '<h1>Hello VIKO</h1>'), 'test.html', 'documents')
print('Saved:', p)
print('URL:', file_url(p))
print('List:', list_files('documents'))
p2 = save_file(wireframe_template('Login', [{'type':'input','label':'Email','x':40,'y':60,'w':200,'h':36}]), 'login.html', 'wireframes')
print('Wireframe:', p2)
p3 = save_file(presentation_template('Q2', [{'title':'Revenue','content':'<p>Up 20%</p>'}]), 'q2.html', 'presentations')
print('Presentation:', p3)
"
```

Expected: prints 3 paths under `workspace/`, no errors.

- [ ] **Step 4: Commit**

```bash
git add workspace/ viko/workspace.py
git commit -m "feat: add workspace folder + template helpers"
```

---

## Task 2: PyQt6-WebEngine dependency

**Files:**
- Modify: `requirements.txt`
- Install in venv

- [ ] **Step 1: Add to requirements.txt**

Open `requirements.txt` and add after `PyQt6`:
```
PyQt6-WebEngine
```

- [ ] **Step 2: Install**

```bash
.venv/bin/pip install PyQt6-WebEngine
```

Expected: resolves and installs `PyQt6-WebEngine` and `PyQt6-WebEngine-Qt6`.

- [ ] **Step 3: Verify import**

```bash
.venv/bin/python -c "from PyQt6.QtWebEngineWidgets import QWebEngineView; print('QWebEngineView OK')"
```

Expected: `QWebEngineView OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add PyQt6-WebEngine dependency"
```

---

## Task 3: viko/browser_panel.py — BrowserPanel widget

**Files:**
- Create: `viko/browser_panel.py`

The panel has three layers stacked vertically:
1. URL bar row (back, forward, refresh, home, URL input, mode badge, devtools toggle)
2. QSplitter (vertical): QWebEngineView on top, DevTools view below (hidden by default)
3. Screenshot label (for headless mode, hidden by default)

Set CDP remote debugging port via env var **before** QApplication is created (done in `viko/ui.py`, Task 5).

- [ ] **Step 1: Create viko/browser_panel.py**

```python
# viko/browser_panel.py
from __future__ import annotations
import os

from PyQt6.QtCore    import Qt, QUrl, pyqtSignal
from PyQt6.QtGui     import QPixmap, QImage
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QSplitter,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore    import QWebEnginePage

from viko.ui_theme import PRI, AMB, DIM, pri, F

CDP_PORT = int(os.environ.get("VIKO_CDP_PORT", "9222"))


class BrowserPanel(QWidget):
    page_loaded    = pyqtSignal(str)   # url
    title_changed  = pyqtSignal(str)   # page title

    def __init__(self, parent=None):
        super().__init__(parent)
        self._headless = False
        self._devtools_visible = False
        self._setup_ui()
        self._connect_signals()

    # ── UI ────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # URL bar
        bar = QWidget(); bar.setFixedHeight(36)
        bar.setStyleSheet("background: #010d14; border-bottom: 1px solid rgba(0,212,255,30);")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(6, 4, 6, 4); bl.setSpacing(4)

        def _nav_btn(label: str, tip: str) -> QPushButton:
            b = QPushButton(label)
            b.setFixedSize(26, 26); b.setFont(F(10))
            b.setToolTip(tip)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(0,212,255,10); color: {PRI.name()};
                    border: 1px solid rgba(0,212,255,30); border-radius: 4px;
                }}
                QPushButton:hover {{ background: rgba(0,212,255,30); }}
                QPushButton:disabled {{ color: rgba(0,212,255,30); }}
            """)
            return b

        self._back_btn    = _nav_btn("‹", "Back")
        self._fwd_btn     = _nav_btn("›", "Forward")
        self._reload_btn  = _nav_btn("⟳", "Reload")
        self._home_btn    = _nav_btn("⌂", "Home (workspace)")

        self._url_bar = QLineEdit()
        self._url_bar.setFont(F(9))
        self._url_bar.setPlaceholderText("https:// or file://")
        self._url_bar.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(0,8,18,200); color: {PRI.name()};
                border: 1px solid rgba(0,212,255,40); border-radius: 4px;
                padding: 2px 8px;
            }}
            QLineEdit:focus {{ border-color: rgba(0,212,255,120); }}
        """)

        self._mode_badge = QLabel("WEB")
        self._mode_badge.setFont(F(7, True))
        self._mode_badge.setFixedWidth(38)
        self._mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode_badge.setStyleSheet(f"color: {PRI.name()}; background: rgba(0,212,255,15); border-radius: 3px; padding: 2px;")

        self._devtools_btn = _nav_btn("⚙", "Toggle DevTools")
        self._devtools_btn.setCheckable(True)

        for w in (self._back_btn, self._fwd_btn, self._reload_btn, self._home_btn):
            bl.addWidget(w)
        bl.addWidget(self._url_bar, 1)
        bl.addWidget(self._mode_badge)
        bl.addWidget(self._devtools_btn)
        root.addWidget(bar)

        # Splitter: web view + devtools
        self._splitter = QSplitter(Qt.Orientation.Vertical)

        self._web_view = QWebEngineView()
        self._web_view.setStyleSheet("background: #000;")
        self._splitter.addWidget(self._web_view)

        self._devtools_view = QWebEngineView()
        self._devtools_view.setVisible(False)
        self._splitter.addWidget(self._devtools_view)
        self._splitter.setSizes([700, 300])

        self._web_view.page().setDevToolsPage(self._devtools_view.page())

        # Screenshot label (headless mode)
        self._screenshot_lbl = QLabel()
        self._screenshot_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._screenshot_lbl.setStyleSheet("background: #000;")
        self._screenshot_lbl.setVisible(False)

        root.addWidget(self._splitter, 1)
        root.addWidget(self._screenshot_lbl, 1)

    def _connect_signals(self):
        self._back_btn.clicked.connect(self._web_view.back)
        self._fwd_btn.clicked.connect(self._web_view.forward)
        self._reload_btn.clicked.connect(self._web_view.reload)
        self._home_btn.clicked.connect(self._go_home)
        self._url_bar.returnPressed.connect(self._on_url_entered)
        self._devtools_btn.toggled.connect(self._toggle_devtools)

        self._web_view.urlChanged.connect(self._on_url_changed)
        self._web_view.titleChanged.connect(self._on_title_changed)
        self._web_view.loadFinished.connect(self._on_load_finished)

    # ── Public API ────────────────────────────────────────────────────────
    def navigate(self, url: str) -> None:
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url
        self._web_view.load(QUrl(url))
        self._update_badge(url)

    def set_headless(self, headless: bool) -> None:
        self._headless = headless
        self._splitter.setVisible(not headless)
        self._screenshot_lbl.setVisible(headless)

    def show_screenshot(self, png_bytes: bytes) -> None:
        img = QImage.fromData(png_bytes)
        self._screenshot_lbl.setPixmap(
            QPixmap.fromImage(img).scaled(
                self._screenshot_lbl.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def current_url(self) -> str:
        return self._web_view.url().toString()

    def page(self) -> QWebEnginePage:
        return self._web_view.page()

    # ── Slots ─────────────────────────────────────────────────────────────
    def _go_home(self):
        from viko.workspace import WORKSPACE
        self.navigate((WORKSPACE / "documents").as_uri())

    def _on_url_entered(self):
        self.navigate(self._url_bar.text().strip())

    def _on_url_changed(self, qurl: QUrl):
        url = qurl.toString()
        self._url_bar.setText(url)
        self._update_badge(url)
        self.page_loaded.emit(url)

    def _on_title_changed(self, title: str):
        self.title_changed.emit(title)

    def _on_load_finished(self, ok: bool):
        self._back_btn.setEnabled(self._web_view.history().canGoBack())
        self._fwd_btn.setEnabled(self._web_view.history().canGoForward())

    def _toggle_devtools(self, checked: bool):
        self._devtools_visible = checked
        self._devtools_view.setVisible(checked)
        if checked:
            self._splitter.setSizes([600, 300])
        else:
            self._splitter.setSizes([1, 0])

    def _update_badge(self, url: str):
        if url.startswith("file://"):
            self._mode_badge.setText("LOCAL")
            self._mode_badge.setStyleSheet(f"color: {AMB.name()}; background: rgba(255,179,71,15); border-radius: 3px; padding: 2px;")
        else:
            self._mode_badge.setText("WEB")
            self._mode_badge.setStyleSheet(f"color: {PRI.name()}; background: rgba(0,212,255,15); border-radius: 3px; padding: 2px;")
```

- [ ] **Step 2: Verify import (no display)**

```bash
.venv/bin/python -c "
import os; os.environ['DISPLAY'] = ''
from viko.browser_panel import BrowserPanel, CDP_PORT
print('BrowserPanel OK, CDP port:', CDP_PORT)
"
```

Expected: `BrowserPanel OK, CDP port: 9222`

- [ ] **Step 3: Commit**

```bash
git add viko/browser_panel.py
git commit -m "feat: add BrowserPanel widget with QWebEngineView + DevTools"
```

---

## Task 4: viko/agent_browser.py — agent-browser subprocess wrapper

**Files:**
- Create: `viko/agent_browser.py`

agent-browser runs as an npx subprocess. It exposes an HTTP server that accepts POST /screenshot and POST /action requests. The package is `@vercel-labs/agent-browser`.

- [ ] **Step 1: Create viko/agent_browser.py**

```python
# viko/agent_browser.py
"""
Wrapper for Vercel Labs agent-browser Node.js subprocess.
Requires: Node.js + npx installed on the system.
Package: npx @vercel-labs/agent-browser
"""
from __future__ import annotations
import subprocess
import threading
import time
import urllib.request
import urllib.error
import json
import logging

logger = logging.getLogger(__name__)

_DEFAULT_PORT = 3500
_PACKAGE      = "@vercel-labs/agent-browser"


class AgentBrowserServer:
    def __init__(self, port: int = _DEFAULT_PORT, cdp_url: str = "http://localhost:9222"):
        self._port    = port
        self._cdp_url = cdp_url
        self._proc: subprocess.Popen | None = None
        self._lock    = threading.Lock()

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self._port}"

    def start(self) -> bool:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return True
            try:
                self._proc = subprocess.Popen(
                    ["npx", "--yes", _PACKAGE,
                     "--port", str(self._port),
                     "--cdp",  self._cdp_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                # Wait up to 5s for server to be ready
                for _ in range(25):
                    time.sleep(0.2)
                    if self.is_running():
                        logger.info("agent-browser started on port %s", self._port)
                        return True
                logger.warning("agent-browser did not start in time")
                return False
            except FileNotFoundError:
                logger.error("npx not found — Node.js must be installed")
                return False
            except Exception as exc:
                logger.error("agent-browser start failed: %s", exc)
                return False

    def stop(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None
        logger.info("agent-browser stopped")

    def is_running(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.base_url}/health", timeout=1)
            return True
        except Exception:
            return False

    def get_screenshot(self) -> bytes:
        req = urllib.request.Request(
            f"{self.base_url}/screenshot",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()

    def send_action(self, action: dict) -> dict:
        payload = json.dumps(action).encode()
        req = urllib.request.Request(
            f"{self.base_url}/action",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())


# Module-level singleton
_server: AgentBrowserServer | None = None
_srv_lock = threading.Lock()


def get_server(port: int = _DEFAULT_PORT, cdp_url: str = "http://localhost:9222") -> AgentBrowserServer:
    global _server
    with _srv_lock:
        if _server is None:
            _server = AgentBrowserServer(port=port, cdp_url=cdp_url)
    return _server
```

- [ ] **Step 2: Lint check**

```bash
.venv/bin/python -m pyflakes viko/agent_browser.py
```

Expected: no output (clean).

- [ ] **Step 3: Commit**

```bash
git add viko/agent_browser.py
git commit -m "feat: add agent-browser Node.js subprocess wrapper"
```

---

## Task 5: viko/skills/browser_tool.py — AI browser skill

**Files:**
- Create: `viko/skills/browser_tool.py`

This skill provides the 4 AI-facing tools. It talks to the BrowserPanel via a shared reference stored in a module-level `_player` variable (same pattern as other skills using `player` arg).

- [ ] **Step 1: Create viko/skills/browser_tool.py**

```python
# viko/skills/browser_tool.py
"""
AI-facing browser tools for the VIKO embedded browser.
navigate_browser  — open URL in embedded browser
render_content    — save HTML to workspace + open in browser
take_screenshot   — screenshot of current page (PNG base64)
get_page_content  — return page text for AI to read
"""
from __future__ import annotations
import base64
import asyncio


def navigate_browser(parameters: dict, player=None) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        return "Error: url is required."
    if not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url
    if player and hasattr(player, "set_browser_url"):
        player.set_browser_url(url)
        player.toggle_browser(visible=True)
        return f"Opened in browser: {url}"
    return f"Browser not available. URL: {url}"


def render_content(parameters: dict, player=None) -> str:
    content  = parameters.get("content", "")
    filename = parameters.get("filename", "output.html")
    category = parameters.get("category", "documents")
    if not content:
        return "Error: content is required."
    if not filename.endswith(".html"):
        filename += ".html"
    from viko.workspace import save_file, file_url
    path = save_file(content, filename, category)
    url  = file_url(path)
    if player and hasattr(player, "set_browser_url"):
        player.set_browser_url(url)
        player.toggle_browser(visible=True)
    return f"Rendered: {path.name} ({category}) → {url}"


def take_screenshot(parameters: dict, player=None) -> str:
    """
    Takes a screenshot of the current browser page.
    Returns base64-encoded PNG string (for AI to inspect).
    Also saves to workspace/documents/screenshot_latest.png.
    """
    if not player or not hasattr(player, "_win"):
        return "Browser not available."
    try:
        import asyncio as _asyncio
        from PyQt6.QtCore import QEventLoop

        loop_result = []

        def _capture():
            panel = getattr(player._win, "_browser", None)
            if panel is None:
                loop_result.append(None)
                return
            page = panel.page()
            el = QEventLoop()

            def _done(img):
                loop_result.append(img)
                el.quit()

            page.grab().finished.connect(_done)  # type: ignore[attr-defined]

        # Run capture synchronously via Qt event loop trick
        panel = getattr(player._win, "_browser", None)
        if panel is None:
            return "Browser panel not initialised."

        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        captured = []

        def _grab():
            px = panel.grab()
            from viko.workspace import WORKSPACE, ensure_dirs
            ensure_dirs()
            out = WORKSPACE / "documents" / "screenshot_latest.png"
            px.save(str(out))
            img_bytes = out.read_bytes()
            captured.append(base64.b64encode(img_bytes).decode())

        QTimer.singleShot(0, _grab)
        QApplication.processEvents()
        import time; time.sleep(0.3)
        QApplication.processEvents()

        if captured:
            return f"Screenshot taken. Base64 length: {len(captured[0])} chars. Saved to workspace/documents/screenshot_latest.png"
        return "Screenshot capture failed."

    except Exception as exc:
        return f"Screenshot error: {exc}"


def get_page_content(parameters: dict, player=None) -> str:
    """Returns visible text content of current browser page."""
    if not player or not hasattr(player, "_win"):
        return "Browser not available."
    panel = getattr(player._win, "_browser", None)
    if panel is None:
        return "Browser panel not initialised."
    result = []
    done   = [False]

    def _cb(text):
        result.append(text)
        done[0] = True

    panel.page().toPlainText(_cb)

    from PyQt6.QtWidgets import QApplication
    import time
    for _ in range(30):
        QApplication.processEvents()
        if done[0]:
            break
        time.sleep(0.1)

    text = result[0] if result else ""
    return text[:8000] if text else "(empty page)"
```

- [ ] **Step 2: Lint check**

```bash
.venv/bin/python -m pyflakes viko/skills/browser_tool.py
```

Expected: no output (clean).

- [ ] **Step 3: Commit**

```bash
git add viko/skills/browser_tool.py
git commit -m "feat: add browser_tool AI skill (navigate, render, screenshot, page_content)"
```

---

## Task 6: viko/ui.py — center QStackedWidget + 🌐 button

**Files:**
- Modify: `viko/ui.py`

Changes:
1. Set CDP env var before QApplication
2. Import BrowserPanel
3. Replace `self._hud = HudCanvas(); blay.addWidget(self._hud, 1)` with QStackedWidget
4. Add 🌐 button between RST and STOP in button bar
5. Add `_toggle_browser()`, `_on_page_loaded()` methods
6. Expose `set_browser_url()`, `toggle_browser()` in VikoUI facade
7. Store `_browser` ref for browser_tool skill

- [ ] **Step 1: Add CDP env var + BrowserPanel import**

In `viko/ui.py`, at the very top (after `from __future__ import annotations`, before other imports):

```python
# Set CDP debug port before QApplication is created
import os as _os
_os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--remote-debugging-port=9222")
```

Then add to the existing widget import block:
```python
from viko.browser_panel import BrowserPanel
```

- [ ] **Step 2: Replace center HudCanvas with QStackedWidget**

Find this block in `_build()` (around line 167):
```python
self._hud = HudCanvas()
blay.addWidget(self._hud, 1)
```

Replace with:
```python
self._hud = HudCanvas()
self._browser = BrowserPanel()
self._center_stack = QStackedWidget()
self._center_stack.addWidget(self._hud)      # index 0
self._center_stack.addWidget(self._browser)  # index 1
self._center_stack.setCurrentIndex(0)
blay.addWidget(self._center_stack, 1)
self._browser.page_loaded.connect(self._on_page_loaded)
```

- [ ] **Step 3: Add 🌐 button to button bar**

In `_build()`, find the block that adds `self._rst_btn` then `self._pause_btn`. Insert the browser button between them:

```python
self._browser_btn = QPushButton("🌐"); self._browser_btn.setFixedSize(28, 26)
self._browser_btn.setFont(F(10))
self._browser_btn.setCursor(Qt.CursorShape.PointingHandCursor)
self._browser_btn.setToolTip("Toggle browser")
self._browser_btn.setCheckable(True)
self._browser_btn.setStyleSheet(_ss())
self._browser_btn.clicked.connect(self._toggle_browser)
bbl.addWidget(self._browser_btn)
```

Add this after `bbl.addWidget(self._rst_btn)` and before `bbl.addWidget(self._pause_btn)`.

- [ ] **Step 4: Add _toggle_browser and _on_page_loaded methods**

In `MainWindow`, add after `_toggle_fullscreen`:
```python
def _toggle_browser(self, visible: bool | None = None):
    if visible is None:
        visible = self._center_stack.currentIndex() == 0
    idx = 1 if visible else 0
    self._center_stack.setCurrentIndex(idx)
    self._browser_btn.setChecked(visible)
    self._browser_btn.setStyleSheet(self._btn_ss(visible))

def _on_page_loaded(self, url: str):
    is_local = url.startswith("file://")
    self._browser_btn.setToolTip(f"Browser: {url[:60]}")

def set_browser_url(self, url: str):
    self._browser.navigate(url)

def set_browser_visible(self, visible: bool):
    self._toggle_browser(visible)
```

- [ ] **Step 5: Expose in VikoUI facade**

In the `VikoUI` class, add:
```python
def set_browser_url(self, url: str): self._win.set_browser_url(url)
def toggle_browser(self, visible: bool | None = None): self._win._toggle_browser(visible)
```

- [ ] **Step 6: Lint check**

```bash
.venv/bin/python -m pyflakes viko/ui.py
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add viko/ui.py
git commit -m "feat: embed BrowserPanel in center QStackedWidget, add browser toggle button"
```

---

## Task 7: viko.py — tool declarations + handlers

**Files:**
- Modify: `viko.py`

Add 4 new tool declarations and 4 new elif branches in `_execute_tool()`.

- [ ] **Step 1: Add imports**

In `viko.py` imports section, add:
```python
from viko.skills.browser_tool import (
    navigate_browser, render_content,
    take_screenshot, get_page_content,
)
```

- [ ] **Step 2: Add tool declarations**

In `TOOL_DECLARATIONS` list, append before the closing `]`:

```python
{
    "name": "navigate_browser",
    "description": (
        "Opens a URL in the VIKO embedded browser panel. "
        "Use for: showing websites, opening search results, displaying content inside VIKO. "
        "This opens the INTERNAL browser, not the system browser."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "Full URL (https://...) or domain (github.com)"},
        },
        "required": ["url"]
    }
},
{
    "name": "render_content",
    "description": (
        "Generate an HTML file and display it in the VIKO embedded browser. "
        "Use for: wireframes, presentations, dashboards, documents, any visual output. "
        "AI generates the HTML content; this saves it to workspace/ and opens it."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "content":  {"type": "STRING", "description": "Full HTML content to render"},
            "filename": {"type": "STRING", "description": "Filename e.g. login-wireframe.html"},
            "category": {"type": "STRING", "description": "wireframes | presentations | documents | code"},
        },
        "required": ["content", "filename"]
    }
},
{
    "name": "take_screenshot",
    "description": "Take a screenshot of the current embedded browser page. Returns description of what was captured.",
    "parameters": {"type": "OBJECT", "properties": {}, "required": []}
},
{
    "name": "get_page_content",
    "description": "Get the visible text content of the current embedded browser page for AI analysis.",
    "parameters": {"type": "OBJECT", "properties": {}, "required": []}
},
```

- [ ] **Step 3: Add handlers in _execute_tool()**

In `_execute_tool()`, add before the `else: result = f"Unknown tool: {name}"` branch:

```python
elif name == "navigate_browser":
    r = await loop.run_in_executor(None, lambda: navigate_browser(parameters=args, player=self.ui))
    result = r or "Done."

elif name == "render_content":
    r = await loop.run_in_executor(None, lambda: render_content(parameters=args, player=self.ui))
    result = r or "Done."

elif name == "take_screenshot":
    r = await loop.run_in_executor(None, lambda: take_screenshot(parameters=args, player=self.ui))
    result = r or "Done."

elif name == "get_page_content":
    r = await loop.run_in_executor(None, lambda: get_page_content(parameters=args, player=self.ui))
    result = r or "(empty)"
```

- [ ] **Step 4: Update system prompt to tell Viko about browser tools**

In `viko/prompt.txt`, add to the TOOL SELECTION section:
```
- navigate_browser → buka URL di embedded browser VIKO (bukan browser sistem)
- render_content → generate HTML/wireframe/presentasi → tampil langsung di browser VIKO
- take_screenshot → screenshot halaman browser saat ini
- get_page_content → baca teks halaman browser untuk analisis
```

- [ ] **Step 5: Lint check**

```bash
.venv/bin/python -m pyflakes viko.py
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add viko.py viko/prompt.txt
git commit -m "feat: add navigate_browser/render_content/screenshot/page_content tool declarations"
```

---

## Task 8: End-to-end test + restart

- [ ] **Step 1: Install PyQt6-WebEngine if not done**

```bash
.venv/bin/pip install PyQt6-WebEngine
.venv/bin/python -c "from PyQt6.QtWebEngineWidgets import QWebEngineView; print('OK')"
```

- [ ] **Step 2: Full lint check**

```bash
.venv/bin/python -m pyflakes viko/workspace.py viko/browser_panel.py viko/agent_browser.py viko/skills/browser_tool.py viko/ui.py viko.py
```

Expected: no output.

- [ ] **Step 3: Restart app**

```bash
pkill -f "python.*viko.py"; sleep 0.5 && .venv/bin/python viko.py &
sleep 4 && ps aux | grep "viko.py" | grep -v grep
```

Expected: process running.

- [ ] **Step 4: Manual test — browser toggle**

Click 🌐 button in VIKO button bar.
Expected: center area switches from HUD to browser panel with URL bar.

- [ ] **Step 5: Manual test — navigate**

Say "viko, buka github.com di browser"
Expected: VIKO calls `navigate_browser`, browser panel shows github.com, badge shows "WEB".

- [ ] **Step 6: Manual test — render wireframe**

Say "viko, buat wireframe halaman login dengan field email, password, dan tombol login"
Expected: VIKO calls `render_content`, saves `wireframes/login-wireframe.html`, browser opens it, badge shows "LOCAL".

- [ ] **Step 7: Manual test — DevTools**

Click ⚙ button in browser URL bar.
Expected: DevTools panel appears in split below the page.

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "feat: VIKO embedded browser + workspace + AI render tools complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ Visible browser (QWebEngineView) + headless mode (screenshot label)
- ✅ Opsi A: center HUD replaced via QStackedWidget
- ✅ 🌐 shortcut button in button bar between RST and STOP
- ✅ DevTools/Inspect (QSplitter split panel)
- ✅ User can click/input (QWebEngineView is fully interactive)
- ✅ workspace/ folder (wireframes, presentations, documents, code)
- ✅ AI tools: navigate_browser, render_content, take_screenshot, get_page_content
- ✅ agent-browser Node.js subprocess wrapper
- ✅ Templates: html_template, wireframe_template, presentation_template (Reveal.js)
- ✅ CDP port exposed for Playwright connection
- ✅ Mode badge: WEB vs LOCAL
- ✅ PyQt6-WebEngine in requirements.txt

**Gaps / notes:**
- agent-browser `get_server()` is created but not yet auto-started — add `get_server().start()` in a background thread in `viko.py`'s `main()` after the API key is available, if needed.
- `take_screenshot` uses `panel.grab()` (Qt widget grab) which works without Playwright. For pixel-perfect browser screenshots, a Playwright-via-CDP approach can replace this later.
- The `@vercel-labs/agent-browser` HTTP API shape (`/health`, `/screenshot`, `/action`) is assumed based on the repo description — verify actual endpoints once installed via `npx --yes @vercel-labs/agent-browser --help`.
