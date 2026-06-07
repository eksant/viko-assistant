# VIKO Code Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix 8 confirmed bugs/issues from code review — 6 correctness bugs, 2 performance fixes, 1 architecture improvement — without refactoring beyond the identified scope.

**Architecture:** Each task is independent and touches a distinct file or function. Tasks 2–6 can be executed in parallel. Task 7 (polling bridge) and Task 8 (llm max_tokens) are fully independent of all others. Tests use pytest + unittest.mock; async tests use `asyncio.run()` in sync wrappers.

**Tech Stack:** Python 3.11+, pytest, asyncio, numpy, resemblyzer, anthropic SDK, google-genai

---

## File Map

| File | Tasks | Change |
|------|-------|--------|
| `viko/core/speaker_verifier.py` | 2 | Zero-norm guard + embedding cache + is_enrolled cache |
| `viko/core/memory.py` | 3 | None-guard on generate_text result |
| `viko/self_engineer/llm.py` | 8 | Add optional `max_tokens` parameter |
| `viko.py` | 1, 4, 5, 6, 7 | QueueFull guard, verify_buf clear, offline threshold, handle cancel, bridge refactor |
| `tests/core/test_speaker_verifier.py` | 2 | New test file |
| `tests/core/test_memory.py` | 3 | New test file |
| `tests/core/test_llm.py` | 8 | New test file |

---

## Task 1: Guard audio_in_queue.put_nowait against QueueFull

**Files:**
- Modify: `viko.py` (line ~1280 inside `_receive_audio`)

This is the crash already observed today. `put_nowait` raises `asyncio.QueueFull` when the
queue (maxsize=200) overflows during a tool call stall. The exception propagates through
`_receive_audio`, kills the TaskGroup, and disconnects the session. Fix: catch and drop.

- [x] **Step 1: Locate the exact line**

```bash
grep -n "audio_in_queue.put_nowait" /Users/eksa/Projects/viko-assistant/viko.py
```

Expected output: one line like `1280:                        self.audio_in_queue.put_nowait(response.data)`

- [x] **Step 2: Wrap with try/except QueueFull**

In `_receive_audio`, find:
```python
                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)
```

Replace with:
```python
                    if response.data:
                        try:
                            self.audio_in_queue.put_nowait(response.data)
                        except asyncio.QueueFull:
                            pass  # drop chunk under load; preferable to crashing
```

- [x] **Step 3: Verify syntax**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -c "import viko"
```

Expected: no output (clean import).

- [x] **Step 4: Commit**

```bash
git add viko.py
git commit -m "fix: drop audio chunk on QueueFull instead of crashing session"
```

---

## Task 2: Fix SpeakerVerifier — zero-norm guard + cache profile + cache is_enrolled

**Files:**
- Modify: `viko/core/speaker_verifier.py`
- Create: `tests/core/test_speaker_verifier.py`

Three bugs in one file:
1. `similarity()` divides by zero if resemblyzer returns a zero-vector → NaN propagates silently
2. `np.load()` reads from disk on every similarity call (~every 2s)
3. `is_enrolled()` calls `Path.exists()` on every 64ms audio chunk (~16/s)

- [x] **Step 1: Create test file**

```bash
mkdir -p /Users/eksa/Projects/viko-assistant/tests/core
touch /Users/eksa/Projects/viko-assistant/tests/core/__init__.py
```

- [x] **Step 2: Write failing tests**

Create `tests/core/test_speaker_verifier.py`:

```python
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from viko.core.speaker_verifier import SpeakerVerifier


def _make_verifier_with_profile(tmp_path: Path, embedding: np.ndarray) -> SpeakerVerifier:
    """Helper: create a SpeakerVerifier with a saved profile."""
    profile = tmp_path / "voice_profile.npy"
    np.save(str(profile), embedding)
    sv = SpeakerVerifier(profile_path=profile)
    return sv


def _fake_embed(self, pcm_bytes: bytes) -> np.ndarray:
    """Return a fixed unit vector regardless of input."""
    v = np.array([1.0, 0.0, 0.0])
    return v / np.linalg.norm(v)


def test_similarity_zero_norm_returns_zero(tmp_path):
    """similarity() must return 0.0, not NaN, when embedding is a zero vector."""
    sv = _make_verifier_with_profile(tmp_path, np.array([1.0, 0.0, 0.0]))
    # Patch _embed to return a zero vector (degenerate PCM)
    with patch.object(sv, "_embed", return_value=np.zeros(3)):
        result = sv.similarity(b"\x00" * 64)
    assert result == 0.0, f"Expected 0.0, got {result}"
    assert not np.isnan(result), "similarity() must not return NaN"


def test_similarity_loads_profile_once_when_called_twice(tmp_path):
    """np.load should be called only once per similarity() call; profile cached across calls."""
    stored = np.array([1.0, 0.0, 0.0])
    sv = _make_verifier_with_profile(tmp_path, stored)
    with patch.object(sv, "_embed", side_effect=_fake_embed.__get__(sv)):
        with patch("numpy.load", wraps=np.load) as mock_load:
            sv.similarity(b"\x00" * 64)
            sv.similarity(b"\x00" * 64)
            # After caching, second call must NOT hit disk
            assert mock_load.call_count == 1, (
                f"np.load called {mock_load.call_count} times; expected 1 after caching"
            )


def test_is_enrolled_uses_cached_flag(tmp_path):
    """is_enrolled() must not call Path.exists() more than once after enroll()."""
    sv = SpeakerVerifier(profile_path=tmp_path / "voice_profile.npy")
    with patch.object(sv, "_embed", return_value=np.array([1.0, 0.0, 0.0])):
        sv.enroll(b"\x00" * 1024)
    with patch.object(Path, "exists", wraps=Path.exists) as mock_exists:
        sv.is_enrolled()
        sv.is_enrolled()
        sv.is_enrolled()
        assert mock_exists.call_count == 0, (
            "is_enrolled() must use cached flag after enroll(), not call Path.exists()"
        )


def test_enroll_invalidates_embedding_cache(tmp_path):
    """enroll() must invalidate the cached embedding so the next similarity() reloads."""
    stored_v1 = np.array([1.0, 0.0, 0.0])
    sv = _make_verifier_with_profile(tmp_path, stored_v1)
    with patch.object(sv, "_embed", return_value=stored_v1):
        sv.similarity(b"\x00" * 64)  # populates cache

    # Now re-enroll with a different embedding
    stored_v2 = np.array([0.0, 1.0, 0.0])
    with patch.object(sv, "_embed", return_value=stored_v2):
        sv.enroll(b"\x00" * 1024)
        result = sv.similarity(b"\x00" * 64)

    # similarity between stored_v2 and candidate stored_v2 = 1.0
    assert abs(result - 1.0) < 1e-6, f"Expected 1.0 after re-enroll, got {result}"
```

- [x] **Step 3: Run tests to confirm they fail**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/core/test_speaker_verifier.py -v
```

Expected: all 4 tests FAIL (cache not implemented yet, zero-norm not guarded).

- [x] **Step 4: Implement fixes in speaker_verifier.py**

Replace the entire file with:

```python
from __future__ import annotations
import numpy as np
from pathlib import Path

SAMPLE_RATE          = 16000
SIMILARITY_THRESHOLD = 0.65
_PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "memory" / "voice_profile.npy"


class SpeakerVerifier:
    def __init__(self, profile_path: Path = _PROFILE_PATH) -> None:
        self._path              = profile_path
        self._encoder           = None
        self._stored_embedding: np.ndarray | None = None  # cache — invalidated by enroll()
        self._is_enrolled_flag: bool | None = None        # cache — avoids Path.exists() on hot path

    def _load_encoder(self) -> None:
        from resemblyzer import VoiceEncoder
        self._encoder = VoiceEncoder()

    def _embed(self, pcm_bytes: bytes) -> np.ndarray:
        if self._encoder is None:
            self._load_encoder()
        from resemblyzer import preprocess_wav
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        wav   = preprocess_wav(audio, source_sr=SAMPLE_RATE)
        return self._encoder.embed_utterance(wav)

    def is_enrolled(self) -> bool:
        if self._is_enrolled_flag is None:
            self._is_enrolled_flag = self._path.exists()
        return self._is_enrolled_flag

    def enroll(self, pcm_bytes: bytes) -> None:
        embedding = self._embed(pcm_bytes)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(self._path), embedding)
        self._stored_embedding = embedding   # update cache immediately
        self._is_enrolled_flag = True        # mark enrolled without re-stat

    def similarity(self, pcm_bytes: bytes) -> float:
        """Return cosine similarity (0–1); returns 0.0 for unenrolled or zero-norm vectors."""
        if not self.is_enrolled():
            return 1.0
        if self._stored_embedding is None:
            self._stored_embedding = np.load(str(self._path))
        candidate = self._embed(pcm_bytes)
        denom = float(np.linalg.norm(self._stored_embedding) * np.linalg.norm(candidate))
        if denom == 0.0:
            return 0.0
        return float(np.dot(self._stored_embedding, candidate) / denom)

    def verify(self, pcm_bytes: bytes) -> bool:
        return self.similarity(pcm_bytes) >= SIMILARITY_THRESHOLD
```

- [x] **Step 5: Run tests — confirm all pass**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/core/test_speaker_verifier.py -v
```

Expected: 4 PASSED.

- [x] **Step 6: Commit**

```bash
git add viko/core/speaker_verifier.py tests/core/test_speaker_verifier.py tests/core/__init__.py
git commit -m "fix: zero-norm guard and embedding/enrolled caches in SpeakerVerifier"
```

---

## Task 3: Fix None-guard in memory.py

**Files:**
- Modify: `viko/core/memory.py` (lines 156, 198)
- Create: `tests/core/test_memory.py`

`generate_text()` returns `None` when Gemini safety-filters a response. `result.upper()` and
`raw.strip()` both throw `AttributeError` on `None`, which the outer `except Exception` swallows
silently — masking real API errors.

- [x] **Step 1: Write failing tests**

Create `tests/core/test_memory.py`:

```python
import pytest
from unittest.mock import patch


def test_should_extract_memory_returns_false_on_none_result():
    """should_extract_memory() must return False (not crash) when generate_text returns None."""
    from viko.core.memory import should_extract_memory
    with patch("viko.self_engineer.llm.generate_text", return_value=None):
        result = should_extract_memory("hello", "hi there")
    assert result is False


def test_should_extract_memory_returns_true_on_yes():
    """should_extract_memory() returns True when generate_text returns 'YES'."""
    from viko.core.memory import should_extract_memory
    with patch("viko.self_engineer.llm.generate_text", return_value="YES"):
        result = should_extract_memory("my name is Ali", "nice to meet you Ali")
    assert result is True


def test_extract_memory_returns_empty_on_none_result():
    """extract_memory() must return {} (not crash) when generate_text returns None."""
    from viko.core.memory import extract_memory
    with patch("viko.self_engineer.llm.generate_text", return_value=None):
        result = extract_memory("hello", "hi there")
    assert result == {}


def test_extract_memory_parses_valid_json():
    """extract_memory() returns parsed dict on valid JSON response."""
    from viko.core.memory import extract_memory
    json_str = '{"identity": {"name": {"value": "Ali"}}}'
    with patch("viko.self_engineer.llm.generate_text", return_value=json_str):
        result = extract_memory("my name is Ali", "nice to meet you")
    assert result == {"identity": {"name": {"value": "Ali"}}}
```

- [x] **Step 2: Run tests — confirm they fail**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/core/test_memory.py -v
```

Expected: `test_should_extract_memory_returns_false_on_none_result` and
`test_extract_memory_returns_empty_on_none_result` FAIL with AttributeError.

- [x] **Step 3: Fix should_extract_memory (line ~156)**

Find:
```python
        return "YES" in result.upper()
```

Replace with:
```python
        return bool(result) and "YES" in result.upper()
```

- [x] **Step 4: Fix extract_memory (line ~198)**

Find:
```python
        clean = raw.strip()
        clean = re.sub(r"```(?:json)?", "", clean).strip().rstrip("`").strip()
```

Replace with:
```python
        if not raw:
            return {}
        clean = raw.strip()
        clean = re.sub(r"```(?:json)?", "", clean).strip().rstrip("`").strip()
```

- [x] **Step 5: Run tests — confirm all pass**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/core/test_memory.py -v
```

Expected: 4 PASSED.

- [x] **Step 6: Commit**

```bash
git add viko/core/memory.py tests/core/test_memory.py
git commit -m "fix: guard against None return from generate_text in memory extraction"
```

---

## Task 4: Clear verify_buf after re-enrollment

**Files:**
- Modify: `viko.py` (inside `_verify_and_forward`, after enrollment completes ~line 1234)

When re-enrollment completes, `verify_buf` still holds 8 overlap chunks from before enrollment
(possibly from a non-owner who triggered it). The first post-enroll similarity window mixes
old audio with new — potentially blocking the freshly enrolled owner.

- [x] **Step 1: Locate the enrollment completion block**

```bash
grep -n "_enrolling\|enroll_buf\|enroll_target\|verify_buf" /Users/eksa/Projects/viko-assistant/viko.py | head -20
```

Expected: lines showing the `if self._enrolling:` block ending with `continue`.

- [x] **Step 2: Add verify_buf clear**

Find this block (approximately lines 1225–1235):
```python
            # Re-enrollment: collect audio, skip normal processing
            if self._enrolling:
                self._enroll_buf.append(item)
                if len(self._enroll_buf) >= self._enroll_target:
                    self._enrolling = False
                    pcm = b"".join(i["data"] for i in self._enroll_buf)
                    self._enroll_buf = []
                    await loop.run_in_executor(None, self._sv.enroll, pcm)
                    self.ui.write_log("SYS: Suara berhasil didaftarkan.")
                    verified_ok      = True
                    ambiguous_streak = 0
                continue
```

Replace with:
```python
            # Re-enrollment: collect audio, skip normal processing
            if self._enrolling:
                self._enroll_buf.append(item)
                if len(self._enroll_buf) >= self._enroll_target:
                    self._enrolling = False
                    pcm = b"".join(i["data"] for i in self._enroll_buf)
                    self._enroll_buf = []
                    await loop.run_in_executor(None, self._sv.enroll, pcm)
                    self.ui.write_log("SYS: Suara berhasil didaftarkan.")
                    verified_ok      = True
                    ambiguous_streak = 0
                    verify_buf       = []   # discard pre-enroll overlap
                continue
```

- [x] **Step 3: Verify syntax**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -c "import viko"
```

Expected: no output.

- [x] **Step 4: Commit**

```bash
git add viko.py
git commit -m "fix: clear verify_buf after re-enrollment to prevent pre-enroll audio contamination"
```

---

## Task 5: Fix offline STT threshold inconsistency

**Files:**
- Modify: `viko.py` (inside `_offline_mode`, line ~844)

The offline mode calls `self._sv.verify(pcm)` which uses the hardcoded `SIMILARITY_THRESHOLD=0.65`.
The online gate uses `PASS_THRESHOLD=0.60`. A far-field owner voice (sim=0.61–0.64) passes online
but is blocked offline. Promote `PASS_THRESHOLD` to a module-level constant and use it in both paths.

- [x] **Step 1: Find current PASS_THRESHOLD definition**

```bash
grep -n "PASS_THRESHOLD\|BLOCK_THRESHOLD\|SIMILARITY_THRESHOLD" /Users/eksa/Projects/viko-assistant/viko.py | head -10
```

Expected: `PASS_THRESHOLD = 0.60` and `BLOCK_THRESHOLD = 0.55` defined as locals inside `_verify_and_forward`.

- [x] **Step 2: Promote to module-level constants**

Find the constants block near the top of `viko.py` (around `SPEECH_THRESHOLD`, `SILENCE_CHUNKS`, etc.):

```bash
grep -n "SPEECH_THRESHOLD\|SILENCE_CHUNKS\|CHUNK_SIZE\|SEND_SAMPLE" /Users/eksa/Projects/viko-assistant/viko.py | head -10
```

After the last constant in that block, add:

```python
SV_PASS_THRESHOLD  = 0.60  # similarity >= this → verified owner
SV_BLOCK_THRESHOLD = 0.55  # similarity <  this → blocked non-owner
```

- [x] **Step 3: Update _verify_and_forward to use module constants**

Find inside `_verify_and_forward`:
```python
        PASS_THRESHOLD    = 0.60  # far voice can drop to 0.60–0.65; non-owner tops at ~0.545
        BLOCK_THRESHOLD   = 0.55
```

Replace with:
```python
        PASS_THRESHOLD    = SV_PASS_THRESHOLD
        BLOCK_THRESHOLD   = SV_BLOCK_THRESHOLD
```

- [x] **Step 4: Update _offline_mode to use module constant**

Find inside `_offline_mode` (approximately line 844):
```python
                            is_owner = (
                                self._verification_bypass
                                or not self._sv.is_enrolled()
                                or await loop.run_in_executor(
                                    None, self._sv.verify, pcm
                                )
                            )
```

Replace with:
```python
                            sim = await loop.run_in_executor(
                                None, self._sv.similarity, pcm
                            )
                            is_owner = (
                                self._verification_bypass
                                or not self._sv.is_enrolled()
                                or sim >= SV_PASS_THRESHOLD
                            )
```

- [x] **Step 5: Verify syntax**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -c "import viko"
```

Expected: no output.

- [x] **Step 6: Commit**

```bash
git add viko.py
git commit -m "fix: use consistent SV_PASS_THRESHOLD in offline and online speaker verification"
```

---

## Task 6: Cancel _speak_off_handle in _play_audio finally block

**Files:**
- Modify: `viko.py` (inside `_play_audio`, finally block ~line 1413)

When `_play_audio` exits (exception or TaskGroup cancellation), a pending `call_later` debounce
handle may still fire 150ms later. If the session restarts before the timer fires, it calls
`set_speaking(False)` mid-new-response, briefly flipping the UI to LISTENING and potentially
opening the mic while VIKO is speaking.

- [x] **Step 1: Locate the finally block**

```bash
grep -n "finally\|_speak_off_handle\|set_speaking\|stream.stop" /Users/eksa/Projects/viko-assistant/viko.py | grep -A2 -B2 "stream.stop"
```

- [x] **Step 2: Cancel handle in finally**

Find the `finally` block in `_play_audio`:
```python
        except Exception as e:
            print(f"[Viko] Playback error: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()
```

Replace with:
```python
        except Exception as e:
            print(f"[Viko] Playback error: {e}")
            raise
        finally:
            if _speak_off_handle is not None:
                _speak_off_handle.cancel()
            self.set_speaking(False)
            stream.stop()
            stream.close()
```

- [x] **Step 3: Verify syntax**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -c "import viko"
```

Expected: no output.

- [x] **Step 4: Commit**

```bash
git add viko.py
git commit -m "fix: cancel pending speak_off debounce handle when _play_audio exits"
```

---

## Task 7: Replace polling bridge with call_soon_threadsafe

**Files:**
- Modify: `viko.py` (inside `_listen_audio`, lines ~1158–1197)

The current bridge uses a `threading.Queue` + `asyncio.sleep(0.02)` polling loop — adding up to
20ms latency per chunk and waking the event loop 50×/s for nothing. The offline mode already uses
the correct pattern: `loop.call_soon_threadsafe(queue.put_nowait, item)` directly in the
sounddevice callback thread.

- [x] **Step 1: Read the current _listen_audio implementation**

```bash
grep -n "def _listen_audio\|_tq\|call_soon_threadsafe\|asyncio.sleep" /Users/eksa/Projects/viko-assistant/viko.py | head -20
```

- [x] **Step 2: Replace the bridge**

Find inside `_listen_audio` the entire bridge section:

```python
        # Bridge: sounddevice thread → queue.Queue → asyncio raw_queue
        _tq: _queue.Queue = _queue.Queue(maxsize=400)
        _stop = _threading.Event()

        def _audio_thread():
            try:
                with sd.RawInputStream(
                    samplerate=SEND_SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=CHUNK_SIZE,
                ) as stream:
                    print("[Viko] Mic stream open")
                    while not _stop.is_set():
                        data, _ = stream.read(CHUNK_SIZE)
                        with self._speaking_lock:
                            viko_speaking = self._is_speaking
                        if viko_speaking or self.ui.muted or self.ui.paused:
                            continue
                        try:
                            _tq.put_nowait({"data": bytes(data), "mime_type": "audio/pcm"})
                        except Exception:
                            pass  # drop if full
            except Exception as _e:
                print(f"[Viko] Mic error: {_e}")

        t = _threading.Thread(target=_audio_thread, daemon=True)
        t.start()

        try:
            while True:
                # Drain threading.Queue into asyncio raw_queue
                while not _tq.empty():
                    try:
                        self.raw_queue.put_nowait(_tq.get_nowait())
                    except Exception:
                        break
                await asyncio.sleep(0.02)
        finally:
            _stop.set()
```

Replace with:

```python
        loop = asyncio.get_running_loop()
        _stop = _threading.Event()

        def _audio_thread():
            try:
                with sd.RawInputStream(
                    samplerate=SEND_SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=CHUNK_SIZE,
                ) as stream:
                    print("[Viko] Mic stream open")
                    while not _stop.is_set():
                        data, _ = stream.read(CHUNK_SIZE)
                        with self._speaking_lock:
                            viko_speaking = self._is_speaking
                        if viko_speaking or self.ui.muted or self.ui.paused:
                            continue
                        item = {"data": bytes(data), "mime_type": "audio/pcm"}
                        try:
                            loop.call_soon_threadsafe(self.raw_queue.put_nowait, item)
                        except Exception:
                            pass  # drop if full or loop is closed
            except Exception as _e:
                print(f"[Viko] Mic error: {_e}")

        t = _threading.Thread(target=_audio_thread, daemon=True)
        t.start()

        try:
            await asyncio.Event().wait()  # park coroutine; _audio_thread runs independently
        finally:
            _stop.set()
```

- [x] **Step 3: Remove now-unused _queue import if present**

```bash
grep -n "^import queue\|^import queue as\|_queue" /Users/eksa/Projects/viko-assistant/viko.py | head -5
```

If `_queue` alias (`import queue as _queue`) is only used in `_listen_audio`, remove it. If it
is used elsewhere, leave it.

- [x] **Step 4: Verify syntax**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -c "import viko"
```

Expected: no output.

- [x] **Step 5: Commit**

```bash
git add viko.py
git commit -m "perf: replace polling bridge with call_soon_threadsafe, removes up to 20ms mic latency"
```

---

## Task 8: Add max_tokens parameter to generate_text()

**Files:**
- Modify: `viko/self_engineer/llm.py`
- Create: `tests/core/test_llm.py`

After removing `max_tokens` from callers, `generate_text()` defaults to 8096 tokens for every
call — including the `should_extract_memory()` YES/NO gate which only needs 5. This wastes cost
and latency. Adding an optional `max_tokens` parameter lets callers opt into tight limits.

- [x] **Step 1: Write failing tests**

Create `tests/core/test_llm.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_generate_text_passes_max_tokens_to_claude():
    """generate_text(max_tokens=5) must pass max_tokens=5 to Claude, not the default 8096."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="YES")]
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            MockAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_msg

            from viko.self_engineer import llm
            # Reload to pick up mocked env
            import importlib
            importlib.reload(llm)

            llm.generate_text("Say YES or NO", max_tokens=5)

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 5, (
                f"Expected max_tokens=5, got {call_kwargs['max_tokens']}"
            )


def test_generate_text_default_max_tokens_is_8096():
    """generate_text() without max_tokens uses the default of 8096."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="hello")]
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            MockAnthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_msg

            from viko.self_engineer import llm
            import importlib
            importlib.reload(llm)

            llm.generate_text("hello")

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 8096
```

- [x] **Step 2: Run tests — confirm they fail**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/core/test_llm.py::test_generate_text_passes_max_tokens_to_claude -v
```

Expected: FAIL (generate_text has no max_tokens param yet).

- [x] **Step 3: Add max_tokens parameter to generate_text and helpers**

Replace `viko/self_engineer/llm.py` with:

```python
import os


def generate_text(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    """Route to Claude if ANTHROPIC_API_KEY is set, otherwise use Gemini."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _claude(prompt, system, max_tokens)
    return _gemini(prompt, system, max_tokens)


def _claude(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    import anthropic
    client = anthropic.Anthropic()
    kwargs = {
        "model":      "claude-sonnet-4-6",
        "max_tokens": max_tokens if max_tokens is not None else 8096,
        "messages":   [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def _gemini(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    from google import genai
    from google.genai import types
    from viko.core.config import get_gemini_key
    client = genai.Client(api_key=get_gemini_key())
    config_kwargs = {}
    if system:
        config_kwargs["system_instruction"] = system
    if max_tokens is not None:
        config_kwargs["max_output_tokens"] = max_tokens
    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
    return client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt, config=config
    ).text
```

- [x] **Step 4: Update callers with tight token limits**

In `viko/core/memory.py`, update `should_extract_memory`:

Find:
```python
        result = generate_text(
            f"Does this conversation contain ANY of the following?\n"
            ...
            system="You are a memory relevance checker. Reply only YES or NO.",
        )
```

Add `max_tokens=5`:
```python
        result = generate_text(
            f"Does this conversation contain ANY of the following?\n"
            ...
            system="You are a memory relevance checker. Reply only YES or NO.",
            max_tokens=5,
        )
```

In `viko/core/memory.py`, update `extract_memory` call — add `max_tokens=1024`:
```python
        raw = generate_text(
            ...
            system="Return ONLY valid JSON. No markdown, no explanation, no extra text.",
            max_tokens=1024,
        )
```

In `viko/core/conversation.py`, update `summarize_session_async` call — add `max_tokens=300`:
```bash
grep -n "generate_text" /Users/eksa/Projects/viko-assistant/viko/core/conversation.py
```

Find the summarization call and add `max_tokens=300`.

- [x] **Step 5: Run tests — confirm they pass**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/core/test_llm.py -v
```

Expected: 2 PASSED.

- [x] **Step 6: Run all tests**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/ -v
```

Expected: all tests pass (existing self_engineer tests + new core tests).

- [x] **Step 7: Commit**

```bash
git add viko/self_engineer/llm.py viko/core/memory.py viko/core/conversation.py tests/core/test_llm.py
git commit -m "feat: add max_tokens parameter to generate_text(); restore tight limits for YES/NO and summary calls"
```

---

## Final Integration Check

After all tasks are committed:

- [x] **Restart VIKO and verify clean startup**

```bash
pkill -f "python viko.py"; sleep 1
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 5 && tail -15 /tmp/viko.log
```

Expected: `[Viko] Connected.` and `[Viko] Mic stream open` in log, no errors.

- [x] **Run full test suite**

```bash
cd /Users/eksa/Projects/viko-assistant && .venv/bin/python -m pytest tests/ -v
```

Expected: all tests pass.

- [x] **Verify SV log shows cached behavior**

```bash
tail -f /tmp/viko.log | grep "\[SV\]"
```

Expected: `[SV] similarity=0.XXX verified=True` appearing every ~2s when speaking, `[SV] silence window` appearing during silence.
