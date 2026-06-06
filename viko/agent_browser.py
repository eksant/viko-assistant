"""
Wrapper for Vercel Labs agent-browser Node.js subprocess.
Requires: Node.js + npx installed on the system.
Package: @vercel-labs/agent-browser

Provides screenshot + action API via CDP to the embedded QWebEngineView.
Auto-start: call get_server().auto_start_in_background() when browser becomes visible.
"""
from __future__ import annotations
import json
import logging
import subprocess
import threading
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_DEFAULT_PORT = 3500
_PACKAGE      = "@vercel-labs/agent-browser"


class AgentBrowserServer:
    def __init__(self, port: int = _DEFAULT_PORT, cdp_url: str = "http://localhost:9222"):
        self._port    = port
        self._cdp_url = cdp_url
        self._proc: subprocess.Popen | None = None
        self._lock    = threading.Lock()
        self._starting = False

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self._port}"

    # ── Lifecycle ─────────────────────────────────────────────────────────
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
                for _ in range(30):
                    time.sleep(0.3)
                    if self.is_running():
                        logger.info("agent-browser started on :%s", self._port)
                        return True
                logger.warning("agent-browser did not start in time")
                return False
            except FileNotFoundError:
                logger.error("npx not found — Node.js must be installed")
                return False
            except Exception as exc:
                logger.error("agent-browser start failed: %s", exc)
                return False

    def auto_start_in_background(self) -> None:
        """Non-blocking: launch start() in a daemon thread if not already running/starting."""
        if self.is_running() or self._starting:
            return
        self._starting = True

        def _run():
            try:
                self.start()
            finally:
                self._starting = False

        threading.Thread(target=_run, daemon=True, name="agent-browser-start").start()

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

    def ensure_running(self, timeout: float = 10.0) -> bool:
        """Block until server is up or timeout. Returns True if running."""
        if self.is_running():
            return True
        self.auto_start_in_background()
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.4)
            if self.is_running():
                return True
        return False

    # ── API ───────────────────────────────────────────────────────────────
    def get_screenshot(self) -> bytes:
        """Return raw PNG/JPEG bytes of the current browser view via CDP."""
        req = urllib.request.Request(
            f"{self.base_url}/screenshot",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()

    def send_action(self, action: dict) -> dict:
        """
        Send an action to the browser.

        Common action formats (agent-browser uses Playwright-style):
          {"type": "click",    "x": 120, "y": 340}
          {"type": "type",     "text": "hello"}
          {"type": "scroll",   "x": 0, "y": 0, "deltaX": 0, "deltaY": 500}
          {"type": "key",      "key": "Enter"}
          {"type": "navigate", "url": "https://..."}
        """
        payload = json.dumps(action).encode()
        req = urllib.request.Request(
            f"{self.base_url}/action",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=payload,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())


# ── Module-level singleton ────────────────────────────────────────────────
_server: AgentBrowserServer | None = None
_srv_lock = threading.Lock()


def get_server(port: int = _DEFAULT_PORT, cdp_url: str = "http://localhost:9222") -> AgentBrowserServer:
    global _server
    with _srv_lock:
        if _server is None:
            _server = AgentBrowserServer(port=port, cdp_url=cdp_url)
    return _server
