# Offline STT Fallback (faster-whisper) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** When Gemini disconnects, VIKO switches to offline STT (faster-whisper) + OpenRouter LLM + macOS `say` TTS instead of sleeping 3 seconds, so voice interaction continues uninterrupted.

**Architecture:** `run()` calls `_offline_mode()` on disconnect instead of `asyncio.sleep(3)`. `_offline_mode()` opens a new sounddevice stream, buffers chunks using energy-based VAD (RMS threshold), transcribes utterances via `OfflineSTT.transcribe_pcm()` in a thread executor, gets a text reply from `LLMClient.chat()`, and speaks via macOS `say -v Damayanti`. After 60 seconds it returns, `run()` attempts reconnect. UI shows OFFLINE state (red dot, existing status card code).

**Tech Stack:** `faster-whisper>=1.2.1` (Whisper `small`, `int8`, CPU), `sounddevice` (existing), `numpy` (add import), `asyncio.create_subprocess_exec` (macOS `say`), `LLMClient` (existing OpenRouter wrapper)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `requirements.txt` | Add `faster-whisper>=1.2.1` |
| Create | `viko/core/offline_stt.py` | Lazy WhisperModel load, `transcribe_pcm(bytes) -> str` |
| Create | `tests/core/__init__.py` | Test package marker |
| Create | `tests/core/test_offline_stt.py` | 5 unit tests with mocked model |
| Modify | `viko/ui/widgets.py:506-516` | Add `"OFFLINE"` to `set_state()` |
| Modify | `viko/ui/window.py:599` | Exclude `"OFFLINE"` from online indicator |
| Modify | `viko.py` | Add `import numpy as np`, `_rms()`, `_offline_respond()`, `_offline_mode()`, update `run()` |

---

## Task 1: Install faster-whisper

**Files:**
- Modify: `requirements.txt`

- [x] **Step 1: Add to requirements.txt**

In `requirements.txt`, after the `numpy` line, add:
```
faster-whisper>=1.2.1
```

- [x] **Step 2: Install**

```bash
.venv/bin/pip install "faster-whisper>=1.2.1"
```

Expected output ends with: `Successfully installed faster-whisper-1.x.x ctranslate2-4.x.x ...`

- [x] **Step 3: Verify import**

```bash
.venv/bin/python -c "from faster_whisper import WhisperModel; print('OK')"
```

Expected: `OK`

- [x] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add faster-whisper dependency for offline STT"
```

---

## Task 2: Create OfflineSTT class

**Files:**
- Create: `viko/core/offline_stt.py`

- [x] **Step 1: Verify file does not exist yet**

```bash
.venv/bin/python -c "from viko.core.offline_stt import OfflineSTT"
```

Expected: `ModuleNotFoundError: No module named 'viko.core.offline_stt'`

- [x] **Step 2: Create `viko/core/offline_stt.py`**

```python
from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000


class OfflineSTT:
    """Offline speech-to-text via faster-whisper (small/int8/cpu/id).

    Model is lazy-loaded on first transcribe_pcm() call. First call
    downloads ~500 MB to ~/.cache/huggingface/hub/ if not cached.
    """

    MODEL_SIZE = "small"
    LANGUAGE = "id"

    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        from faster_whisper import WhisperModel
        self._model = WhisperModel(
            self.MODEL_SIZE,
            device="cpu",
            compute_type="int8",
        )

    def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> str:
        """Transcribe raw int16 PCM bytes to Indonesian text.

        Safe to call from a thread executor — ctranslate2 releases the GIL.
        """
        if self._model is None:
            self._load()
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(
            audio,
            language=self.LANGUAGE,
            beam_size=5,
            vad_filter=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
```

- [x] **Step 3: Verify import**

```bash
.venv/bin/python -c "from viko.core.offline_stt import OfflineSTT; print('OK')"
```

Expected: `OK`

- [x] **Step 4: Commit**

```bash
git add viko/core/offline_stt.py
git commit -m "feat: add OfflineSTT class (faster-whisper small/int8/cpu/id)"
```

---

## Task 3: Tests for OfflineSTT

**Files:**
- Create: `tests/core/__init__.py`
- Create: `tests/core/test_offline_stt.py`

- [x] **Step 1: Create test package**

Create `tests/core/__init__.py` as an empty file.

- [x] **Step 2: Write the tests**

Create `tests/core/test_offline_stt.py`:

```python
"""Unit tests for viko.core.offline_stt.OfflineSTT (mocked model)."""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from viko.core.offline_stt import OfflineSTT, SAMPLE_RATE


def _make_pcm(seconds: float = 1.0) -> bytes:
    """Generate 1 second of silent int16 PCM."""
    n = int(SAMPLE_RATE * seconds)
    return np.zeros(n, dtype=np.int16).tobytes()


class TestOfflineSTT:
    def test_init_does_not_load_model(self):
        """Model must not be loaded at construction time."""
        stt = OfflineSTT()
        assert stt._model is None

    def test_load_creates_whisper_model(self):
        """_load() must call WhisperModel with expected arguments."""
        stt = OfflineSTT()
        with patch("faster_whisper.WhisperModel") as mock_cls:
            mock_cls.return_value = MagicMock()
            stt._load()
            mock_cls.assert_called_once_with("small", device="cpu", compute_type="int8")
            assert stt._model is not None

    def test_transcribe_pcm_calls_load_on_first_use(self):
        """transcribe_pcm() must call _load() if _model is None."""
        stt = OfflineSTT()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), MagicMock())

        def _fake_load():
            stt._model = mock_model

        with patch.object(stt, "_load", side_effect=_fake_load) as mock_load:
            stt.transcribe_pcm(_make_pcm())
            mock_load.assert_called_once()

    def test_transcribe_pcm_joins_segments(self):
        """transcribe_pcm() must join all segment texts with spaces and strip."""
        stt = OfflineSTT()
        seg1 = MagicMock(text=" halo ")
        seg2 = MagicMock(text=" dunia ")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([seg1, seg2]), MagicMock())
        stt._model = mock_model

        result = stt.transcribe_pcm(_make_pcm())

        assert result == "halo dunia"

    def test_transcribe_empty_segments_returns_empty_string(self):
        """transcribe_pcm() with no segments must return empty string."""
        stt = OfflineSTT()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), MagicMock())
        stt._model = mock_model

        result = stt.transcribe_pcm(_make_pcm())

        assert result == ""
```

- [x] **Step 3: Run to verify all pass**

```bash
.venv/bin/python -m pytest tests/core/test_offline_stt.py -v
```

Expected:
```
PASSED tests/core/test_offline_stt.py::TestOfflineSTT::test_init_does_not_load_model
PASSED tests/core/test_offline_stt.py::TestOfflineSTT::test_load_creates_whisper_model
PASSED tests/core/test_offline_stt.py::TestOfflineSTT::test_transcribe_pcm_calls_load_on_first_use
PASSED tests/core/test_offline_stt.py::TestOfflineSTT::test_transcribe_pcm_joins_segments
PASSED tests/core/test_offline_stt.py::TestOfflineSTT::test_transcribe_empty_segments_returns_empty_string
5 passed
```

- [x] **Step 4: Commit**

```bash
git add tests/core/__init__.py tests/core/test_offline_stt.py
git commit -m "test: add OfflineSTT unit tests (5 tests, mocked model)"
```

---

## Task 4: Add OFFLINE UI state

**Files:**
- Modify: `viko/ui/widgets.py:506-516`
- Modify: `viko/ui/window.py:599`

Context: The status card at `widgets.py:243` already renders "OFFLINE" in red when `_online=False`. The fix is two lines:
1. `set_state("OFFLINE")` falls to `"idle"` in the HUD animation — add explicit case.
2. `_apply_state()` in `window.py` calls `set_online(state != "IDLE")` — OFFLINE must also set online=False.

- [x] **Step 1: Add OFFLINE to HUD `set_state()` in `viko/ui/widgets.py`**

Find the `set_state` method (around line 506). The current body is:
```python
    def set_state(self, state: str):
        """Accept viko.py state strings and map to animation state."""
        s = state.upper()
        if s == "SPEAKING":     self.state = "speaking"
        elif s == "LISTENING":  self.state = "listening"
        elif s == "THINKING":   self.state = "listening"
        elif s == "WORKING":    self.state = "working"
        elif s == "CODING":     self.state = "coding"
        elif s == "MUTED":      self._muted = True; self.state = "idle"
        elif s == "PAUSED":     self.state = "paused"
        else:                   self.state = "idle"
        if s != "MUTED":        self._muted = False
```

Add `elif s == "OFFLINE":` before the final `else`:
```python
    def set_state(self, state: str):
        """Accept viko.py state strings and map to animation state."""
        s = state.upper()
        if s == "SPEAKING":     self.state = "speaking"
        elif s == "LISTENING":  self.state = "listening"
        elif s == "THINKING":   self.state = "listening"
        elif s == "WORKING":    self.state = "working"
        elif s == "CODING":     self.state = "coding"
        elif s == "MUTED":      self._muted = True; self.state = "idle"
        elif s == "PAUSED":     self.state = "paused"
        elif s == "OFFLINE":    self.state = "idle"
        else:                   self.state = "idle"
        if s != "MUTED":        self._muted = False
```

- [x] **Step 2: Update `_apply_state()` in `viko/ui/window.py`**

Find line 599 (inside `_apply_state`):
```python
        self._left.set_online(state != "IDLE")
```

Change to:
```python
        self._left.set_online(state not in ("IDLE", "OFFLINE"))
```

- [x] **Step 3: Lint check**

```bash
.venv/bin/ruff check viko/ui/widgets.py viko/ui/window.py --select F401,F811,F841
```

Expected: no output (no errors).

- [x] **Step 4: Commit**

```bash
git add viko/ui/widgets.py viko/ui/window.py
git commit -m "feat: add OFFLINE state to HUD set_state() and status card"
```

---

## Task 5: Add offline helpers to viko.py

**Files:**
- Modify: `viko.py` — add `import numpy as np`, module-level `_rms()`, and two new `VikoLive` methods

- [x] **Step 1: Add `import numpy as np` to imports**

In `viko.py`, after line 5 (`from pathlib import Path`), add:
```python
import numpy as np
```

Verify it's not already there:
```bash
grep "numpy" viko.py
```

- [x] **Step 2: Add module-level `_rms()` helper**

In `viko.py`, find the module-level helper `_is_ctrl_seq()` (grep for it). Add `_rms()` directly below it:

```python
def _rms(pcm_bytes: bytes) -> float:
    """RMS energy of int16 PCM bytes. Returns 0.0 for empty input."""
    arr = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(arr ** 2))) if arr.size else 0.0
```

- [x] **Step 3: Add `_offline_respond()` to `VikoLive`**

In the `VikoLive` class, add this method after `speak()`:

```python
    async def _offline_respond(self, text: str) -> None:
        """Get LLM reply for text and speak via macOS say. Used in offline mode."""
        loop = asyncio.get_event_loop()
        try:
            from viko.core.client import LLMClient
            system = (
                "Kamu adalah VIKO, asisten AI suara pribadi. "
                "Jawab dalam Bahasa Indonesia, singkat dan jelas (1-2 kalimat). "
                "Mode offline — tidak ada akses internet saat ini."
            )
            reply = await loop.run_in_executor(None, LLMClient().chat, text, system)
        except Exception as _e:
            print(f"[Viko] Offline LLM failed: {_e}")
            reply = "Maaf, saya sedang offline dan tidak bisa menjawab sekarang."

        self.ui.write_log(f"Viko [offline]: {reply}")
        try:
            proc = await asyncio.create_subprocess_exec(
                "say", "-v", "Damayanti", reply,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception:
            try:
                proc = await asyncio.create_subprocess_exec("say", reply)
                await proc.wait()
            except Exception as _e2:
                print(f"[Viko] say failed: {_e2}")
```

- [x] **Step 4: Add `_offline_mode()` to `VikoLive`**

Add this method after `_offline_respond()`:

```python
    async def _offline_mode(self, max_seconds: int = 60) -> None:
        """Offline listen-and-respond loop using faster-whisper + LLM + macOS say.

        VAD constants:
          SPEECH_THRESHOLD=300  — int16 RMS above this = active speech
          SILENCE_CHUNKS=20     — ~1.3s silence (20 × 64ms) ends an utterance
          MIN_SPEECH_CHUNKS=8   — ~512ms min speech before transcribing
        """
        from viko.core.offline_stt import OfflineSTT

        stt = OfflineSTT()
        loop = asyncio.get_event_loop()
        audio_q: asyncio.Queue = asyncio.Queue()

        SPEECH_THRESHOLD  = 300
        SILENCE_CHUNKS    = 20
        MIN_SPEECH_CHUNKS = 8

        def _cb(indata, frames, time_info, status):
            if self.ui.muted or self.ui.paused:
                return
            loop.call_soon_threadsafe(audio_q.put_nowait, indata.tobytes())

        buf:           list[bytes] = []
        silence_count: int  = 0
        speech_count:  int  = 0
        in_speech:     bool = False
        deadline:      float = loop.time() + max_seconds

        with sd.InputStream(
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=_cb,
        ):
            self.ui.write_log("SYS: Mode offline. Whisper aktif.")
            print("[Viko] Offline STT active")

            while loop.time() < deadline:
                try:
                    chunk = await asyncio.wait_for(audio_q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                rms = _rms(chunk)

                if rms > SPEECH_THRESHOLD:
                    buf.append(chunk)
                    speech_count += 1
                    silence_count = 0
                    in_speech = True
                elif in_speech:
                    buf.append(chunk)
                    silence_count += 1
                    if silence_count >= SILENCE_CHUNKS:
                        if speech_count >= MIN_SPEECH_CHUNKS:
                            pcm  = b"".join(buf)
                            text = await loop.run_in_executor(None, stt.transcribe_pcm, pcm)
                            if text.strip():
                                self.ui.write_log(f"You [offline]: {text}")
                                await self._offline_respond(text)
                        buf           = []
                        silence_count = 0
                        speech_count  = 0
                        in_speech     = False

        print("[Viko] Offline mode ended — reconnecting")
```

- [x] **Step 5: Lint check**

```bash
.venv/bin/ruff check viko.py --select F401,F811,F841
```

Expected: no new errors.

- [x] **Step 6: Commit**

```bash
git add viko.py
git commit -m "feat: add _rms(), _offline_mode(), _offline_respond() to VikoLive"
```

---

## Task 6: Integrate into run() loop

**Files:**
- Modify: `viko.py:1218-1221` — replace 3-second sleep with offline mode

- [x] **Step 1: Locate the four target lines in `run()`**

```bash
grep -n "Reconnecting in 3s\|asyncio.sleep(3)" viko.py
```

Expected output: two lines near 1220-1221 in `run()`:
```
1220:            print("[Viko] Reconnecting in 3s...")
1221:            await asyncio.sleep(3)
```

- [x] **Step 2: Replace sleep with offline mode**

Find this block at the bottom of `run()`:
```python
            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[Viko] Reconnecting in 3s...")
            await asyncio.sleep(3)
```

Replace with:
```python
            self.set_speaking(False)
            self.ui.set_state("OFFLINE")
            print("[Viko] Connection lost — offline mode")
            await self._offline_mode()
            self.ui.set_state("THINKING")
            print("[Viko] Reconnecting...")
            await asyncio.sleep(1)
```

- [x] **Step 3: Run all tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: all tests pass (24 self_engineer + 5 offline_stt = 29 total).

- [x] **Step 4: Start VIKO and verify normal startup**

```bash
./scripts/start.sh
sleep 5 && tail -20 /tmp/viko.log
```

Expected log (no OFFLINE state on healthy connection):
```
[Viko] Mic: ... @ 16000Hz
[Viko] Connected.
```

- [x] **Step 5: Commit**

```bash
git add viko.py
git commit -m "feat: integrate offline STT fallback into run() reconnect loop"
```

---

## Notes

**Model storage:** `OfflineSTT._load()` downloads the `small` model (~500 MB) to `models/whisper/` inside the project root. The `models/` folder is gitignored. Download happens once; subsequent loads from disk take ~2-3 seconds on Apple Silicon.

**Background pre-load:** After each Gemini connect, `_warmup_offline_stt()` runs in a background daemon thread. This pre-loads the model into RAM so that offline mode activates instantly when Gemini drops. UI shows `"SYS: Mempersiapkan model offline..."` during warmup and `"SYS: Model offline siap."` when ready.

**Startup/shutdown logging:** App start and shutdown are logged via `viko.core.logger` to `viko/logs/viko.log`. A `=` separator marks each session boundary.

**Indonesian TTS voice:** `say -v Damayanti` requires the Damayanti voice to be installed in System Settings → Accessibility → Spoken Content → System Voice. If not installed, the code falls back to the default English voice. To install: System Settings → Accessibility → Spoken Content → System Voice → Customise → Indonesian → Damayanti.

**VAD tuning:** The `SPEECH_THRESHOLD=300` and `SILENCE_CHUNKS=20` constants are starting points. If VIKO cuts off speech too early, increase `SILENCE_CHUNKS` to 25-30. If background noise triggers false positives, increase `SPEECH_THRESHOLD` to 500-800.

**`speak()` in offline mode:** The existing `speak()` method requires an active Gemini session. `_offline_respond()` bypasses it and calls `say` directly — do not call `self.speak()` from `_offline_mode()`.
