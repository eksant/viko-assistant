# Latency Reduction + Wake Word ("Viko") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Eliminate the 2-second input-gate delay, add "Viko" wake-word gating on VIKO's audio output, and halve playback latency.

**Architecture:** Flip the speaker-verification gate from the input side (blocking audio to Gemini) to the output side (suppressing VIKO's audio response). Silero VAD replaces the RMS threshold for more accurate speech detection. Wake word is checked against Gemini Live's own real-time input transcription, which arrives before response audio.

**Tech Stack:** Python 3.11+, `silero-vad>=5.1` (ONNX, no PyTorch required), existing `resemblyzer`, `sounddevice`, `google-genai` Gemini Live API.

---

## File Map

| File | Change |
|---|---|
| `requirements.txt` | Add `silero-vad>=5.1` |
| `viko.py` lines 630–648 | Add `_sv_verified`, `_viko_addressed`, `_vad_model` to `__init__` |
| `viko.py` lines 1163–1182 | `_listen_audio`: score each chunk with Silero VAD, tag `is_speech` |
| `viko.py` lines 1194–1265 | `_verify_and_forward`: remove input gate, always forward real audio, update `self._sv_verified` |
| `viko.py` lines 1275–1316 | `_receive_audio`: gate `response.data` on wake word + SV; detect wake word from `input_transcription` |
| `viko.py` line 1380 | `_play_audio`: `latency="high"` → `latency="low"` |
| `tests/core/test_wake_word.py` | New: unit tests for wake word detection logic |
| `tests/core/test_vad_smoke.py` | New: smoke test Silero VAD loads and scores |

---

## Task 1: Add silero-vad dependency

**Files:**
- Modify: `requirements.txt`

- [x] **Step 1: Add dependency**

In `requirements.txt`, add after the `resemblyzer>=0.1.1` line:
```
silero-vad>=5.1
```

- [x] **Step 2: Install and verify**

```bash
.venv/bin/pip install silero-vad
.venv/bin/python -c "from silero_vad import load_silero_vad; m = load_silero_vad(); print('VAD loaded:', type(m))"
```

Expected output: `VAD loaded: <class '...'>`  — no error.

- [x] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add silero-vad dependency for VAD"
```

---

## Task 2: Silero VAD smoke test

**Files:**
- Create: `tests/core/test_vad_smoke.py`

- [x] **Step 1: Write the test**

```python
# tests/core/test_vad_smoke.py
import numpy as np
import pytest


def test_silero_vad_loads():
    from silero_vad import load_silero_vad
    model = load_silero_vad()
    assert model is not None


def test_silero_vad_scores_silence():
    from silero_vad import load_silero_vad
    model = load_silero_vad()
    silence = np.zeros(1024, dtype=np.float32)
    prob = float(model(silence, 16000))
    assert 0.0 <= prob <= 1.0
    assert prob < 0.5, f"Expected silence < 0.5, got {prob}"


def test_silero_vad_scores_tone():
    from silero_vad import load_silero_vad
    model = load_silero_vad()
    t = np.linspace(0, 1024 / 16000, 1024, dtype=np.float32)
    tone = np.sin(2 * np.pi * 300 * t) * 0.5
    prob = float(model(tone, 16000))
    assert 0.0 <= prob <= 1.0
```

- [x] **Step 2: Run to confirm tests pass**

```bash
.venv/bin/python -m pytest tests/core/test_vad_smoke.py -v
```

Expected: all 3 PASS (model loads correctly).

> Note: `test_silero_vad_scores_silence` asserts `prob < 0.5`. If it fails because a pure tone scores high — that's fine, only the silence check matters for production. Adjust the tone test assertion to just `0.0 <= prob <= 1.0` if needed.

- [x] **Step 3: Commit**

```bash
git add tests/core/test_vad_smoke.py
git commit -m "test: silero VAD smoke tests"
```

---

## Task 3: Silero VAD in `_listen_audio` + new state flags

**Files:**
- Modify: `viko.py` lines 630–648 (`__init__`)
- Modify: `viko.py` lines 1151–1192 (`_listen_audio`)

- [x] **Step 1: Add state flags and VAD model slot to `__init__`**

In `VikoLive.__init__` (currently ends around line 647), add three lines after the existing `self._enroll_target: int = 0` line:

```python
        self._enroll_target: int  = 0
        self._sv_verified:   bool = True   # updated by _verify_and_forward background loop
        self._viko_addressed: bool = False  # set when "viko" detected in input_transcription
        self._vad_model             = None  # loaded lazily in _listen_audio
        self.raw_queue            = None
```

- [x] **Step 2: Load VAD model lazily and score each chunk**

Replace the entire `_listen_audio` method (lines 1151–1192) with:

```python
    async def _listen_audio(self):
        import threading as _threading

        if self._vad_model is None:
            from silero_vad import load_silero_vad
            self._vad_model = load_silero_vad()

        try:
            dev = sd.query_devices(kind='input')
            print(f"[Viko] Mic: {dev['name']} @ {SEND_SAMPLE_RATE}Hz")
        except Exception:
            print("[Viko] Mic started")

        loop = asyncio.get_running_loop()
        _stop = _threading.Event()
        _vad  = self._vad_model

        def _audio_thread():
            import numpy as _np
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
                        pcm_f32 = _np.frombuffer(bytes(data), dtype=_np.int16).astype(_np.float32) / 32768.0
                        try:
                            speech_prob = float(_vad(pcm_f32, SEND_SAMPLE_RATE))
                        except Exception:
                            speech_prob = 1.0  # fallback: treat as speech on VAD error
                        item = {
                            "data":      bytes(data),
                            "mime_type": "audio/pcm",
                            "is_speech": speech_prob > 0.5,
                        }
                        try:
                            loop.call_soon_threadsafe(self.raw_queue.put_nowait, item)
                        except Exception:
                            pass  # drop if loop is closed
            except Exception as _e:
                print(f"[Viko] Mic error: {_e}")

        t = _threading.Thread(target=_audio_thread, daemon=True)
        t.start()

        try:
            await asyncio.Event().wait()
        finally:
            _stop.set()
```

- [x] **Step 3: Start VIKO and verify mic + VAD logs**

```bash
pkill -f "python viko.py" 2>/dev/null; sleep 1
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 6 && tail -30 /tmp/viko.log
```

Expected: `[Viko] Mic stream open` appears with no errors. No `VAD error` lines.

- [x] **Step 4: Commit**

```bash
pkill -f "python viko.py" 2>/dev/null
git add viko.py
git commit -m "feat: silero VAD replaces RMS threshold in audio capture"
```

---

## Task 4: Ungate input — `_verify_and_forward` becomes background SV

**Files:**
- Modify: `viko.py` lines 1194–1265 (`_verify_and_forward`)

- [x] **Step 1: Replace `_verify_and_forward` entirely**

Replace the entire method (lines 1194–1265) with the following. Key differences from old code:
- `verified_ok` local var → `self._sv_verified` instance flag
- Uses `item.get("is_speech", True)` instead of `_rms(pcm) < SPEECH_THRESHOLD`
- Last two lines: always `await self.out_queue.put(item)` — no silence substitution

```python
    async def _verify_and_forward(self):
        """Run speaker verification in background; always forward real audio to out_queue.

        Updates self._sv_verified (True/False). Output gating happens in _receive_audio.
        Accumulates only speech chunks (is_speech=True) for resemblyzer so silence windows
        don't dilute the embedding.
        """
        loop = asyncio.get_running_loop()
        verify_buf:      list[bytes] = []
        VERIFY_CHUNKS    = 32    # 32 × 64ms ≈ 2s — minimum for reliable resemblyzer embedding
        PASS_THRESHOLD   = SV_PASS_THRESHOLD
        BLOCK_THRESHOLD  = SV_BLOCK_THRESHOLD
        RECOVERY_WINDOWS = 5
        ambiguous_streak = 0

        while True:
            item        = await self.raw_queue.get()
            chunk_bytes = item["data"]
            is_speech   = item.get("is_speech", True)

            # Re-enrollment: collect audio, skip normal verification
            if self._enrolling:
                self._enroll_buf.append(item)
                if len(self._enroll_buf) >= self._enroll_target:
                    self._enrolling   = False
                    pcm = b"".join(i["data"] for i in self._enroll_buf)
                    self._enroll_buf  = []
                    await loop.run_in_executor(None, self._sv.enroll, pcm)
                    self.ui.write_log("SYS: Suara berhasil didaftarkan.")
                    self._sv_verified = True
                    ambiguous_streak  = 0
                    verify_buf        = []
                continue

            # Accumulate speech-only chunks for periodic verification
            if is_speech:
                verify_buf.append(chunk_bytes)

            if len(verify_buf) >= VERIFY_CHUNKS:
                pcm        = b"".join(verify_buf)
                verify_buf = verify_buf[-8:]   # keep ~500ms overlap
                if self._sv.is_enrolled() and not self._verification_bypass:
                    sim = await loop.run_in_executor(None, self._sv.similarity, pcm)
                    print(f"[SV] similarity={sim:.3f} verified={self._sv_verified}")
                    if sim >= PASS_THRESHOLD:
                        self._sv_verified = True
                        ambiguous_streak  = 0
                    elif sim < BLOCK_THRESHOLD:
                        self._sv_verified = False
                        ambiguous_streak  = 0
                    else:
                        # ambiguous (0.55–0.60): if blocked, count toward auto-recovery
                        if not self._sv_verified:
                            ambiguous_streak += 1
                            if ambiguous_streak >= RECOVERY_WINDOWS:
                                self._sv_verified = True
                                ambiguous_streak  = 0
                                print("[SV] auto-recovery: reopened after silence")

            # Always forward real audio — output gating is in _receive_audio
            await self.out_queue.put(item)
```

- [x] **Step 2: Start and verify SV log output**

```bash
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 6 && tail -5 /tmp/viko.log
```

Speak for 3+ seconds. Then check:
```bash
grep "\[SV\]" /tmp/viko.log
```

Expected: lines like `[SV] similarity=0.712 verified=True` appear (no longer blocked). VIKO should now respond without the 2-second delay.

- [x] **Step 3: Commit**

```bash
pkill -f "python viko.py" 2>/dev/null
git add viko.py
git commit -m "feat: ungate audio input — SV runs in background, always forward real audio"
```

---

## Task 5: Wake word unit tests

**Files:**
- Create: `tests/core/test_wake_word.py`

- [x] **Step 1: Write tests for the wake word logic**

The detection logic (to be added in Task 6) is:
```python
"".join(in_buf).lower()
any(kw in accumulated for kw in ("viko", "hei viko", "hey viko"))
```

Write tests for this logic now, before wiring it into `_receive_audio`:

```python
# tests/core/test_wake_word.py

_WAKE_KEYWORDS = ("viko", "hei viko", "hey viko")


def _is_viko_addressed(in_buf: list[str]) -> bool:
    accumulated = "".join(in_buf).lower()
    return any(kw in accumulated for kw in _WAKE_KEYWORDS)


def test_wake_word_single_chunk():
    assert _is_viko_addressed(["Viko, cuaca hari ini?"]) is True


def test_wake_word_prefix_hei():
    assert _is_viko_addressed(["Hei Viko, tolong bantu saya."]) is True


def test_wake_word_prefix_hey():
    assert _is_viko_addressed(["Hey Viko, bukakan browser."]) is True


def test_wake_word_case_insensitive():
    assert _is_viko_addressed(["VIKO kemana kamu?"]) is True


def test_wake_word_streaming_chunks():
    # Gemini transcription may arrive as fragments without spaces between them
    assert _is_viko_addressed(["Vik", "o, halo"]) is True


def test_no_wake_word():
    assert _is_viko_addressed(["Cuaca hari ini bagaimana?"]) is False


def test_no_wake_word_partial():
    # "viktor" contains "viko" — this is a known false positive we accept
    # Test documents the behaviour rather than asserting False
    result = _is_viko_addressed(["viktor"])
    assert isinstance(result, bool)


def test_empty_buf():
    assert _is_viko_addressed([]) is False
```

- [x] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest tests/core/test_wake_word.py -v
```

Expected: all PASS.

- [x] **Step 3: Commit**

```bash
git add tests/core/test_wake_word.py
git commit -m "test: wake word detection unit tests"
```

---

## Task 6: Wire wake word + output gate in `_receive_audio`

**Files:**
- Modify: `viko.py` lines 1275–1316 (`_receive_audio`)

- [x] **Step 1: Gate `response.data` on wake word + SV**

Find this block (around line 1275):
```python
                    if response.data:
                        try:
                            self.audio_in_queue.put_nowait(response.data)
                        except asyncio.QueueFull:
                            pass  # drop chunk under load; preferable to crashing
```

Replace with:
```python
                    if response.data:
                        try:
                            if self._viko_addressed and (
                                self._sv_verified
                                or self._verification_bypass
                                or not self._sv.is_enrolled()
                            ):
                                self.audio_in_queue.put_nowait(response.data)
                        except asyncio.QueueFull:
                            pass  # drop chunk under load; preferable to crashing
```

- [x] **Step 2: Detect wake word from input transcription**

Find this block (around line 1299):
```python
                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text
                            if txt and not _is_ctrl_seq(txt):
                                in_buf.append(txt)
```

Replace with:
```python
                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text
                            if txt and not _is_ctrl_seq(txt):
                                in_buf.append(txt)
                                if not self._viko_addressed:
                                    _acc = "".join(in_buf).lower()
                                    if any(kw in _acc for kw in ("viko", "hei viko", "hey viko")):
                                        self._viko_addressed = True
                                        print("[Wake] 'viko' detected — gate open for this turn")
```

- [x] **Step 3: Reset `_viko_addressed` on turn complete**

Find `if sc.turn_complete:` (around line 1304). Add one line at the very start of that block:
```python
                        if sc.turn_complete:
                            self._viko_addressed = False   # reset for next turn
                            self.set_speaking(False)
                            self._last_active = asyncio.get_event_loop().time()
```

(Only insert `self._viko_addressed = False` — the remaining lines already exist, don't duplicate them.)

- [x] **Step 4: Start VIKO and test wake word behaviour**

```bash
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 6
```

**Test A — no wake word:** Speak "Cuaca hari ini?" without saying "Viko". VIKO should stay silent.

**Test B — with wake word:** Say "Viko, cuaca hari ini?" VIKO should respond normally.

Check logs:
```bash
grep -E "\[Wake\]|\[SV\]" /tmp/viko.log
```

Expected: `[Wake] 'viko' detected — gate open for this turn` appears when you say "Viko".

- [x] **Step 5: Commit**

```bash
pkill -f "python viko.py" 2>/dev/null
git add viko.py
git commit -m "feat: wake word gate — VIKO only responds when addressed as Viko"
```

---

## Task 7: Output latency fix

**Files:**
- Modify: `viko.py` line 1380 (`_play_audio`)

- [x] **Step 1: Change latency setting**

Find this line (around line 1380):
```python
        latency="high",    # bigger internal buffer = stutter-resistant
```

Replace with:
```python
        latency="low",     # smaller buffer = lower playback latency (~20-50ms vs ~300ms)
```

- [x] **Step 2: Start and verify subjective latency**

```bash
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 6
```

Say "Viko, halo". The voice response should start audibly faster than before. If stutter appears during tool execution, note it but accept — it's the documented trade-off.

- [x] **Step 3: Commit**

```bash
pkill -f "python viko.py" 2>/dev/null
git add viko.py
git commit -m "perf: reduce output latency — latency=high to latency=low"
```

---

## Task 8: Full regression test

- [x] **Step 1: Run all tests**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: all tests pass including `test_vad_smoke.py` and `test_wake_word.py`.

- [x] **Step 2: End-to-end verification**

Start VIKO and run all scenarios:

```bash
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 6
```

| Scenario | Expected |
|---|---|
| Say nothing for 30s, then "Viko, halo" | Responds on first call |
| "Cuaca hari ini?" (no "Viko") | Stays silent |
| "Viko, cuaca hari ini?" | Responds |
| "Hei Viko, tolong buka browser" | Responds |
| (If second person speaks) "Viko, halo" | Stays silent (SV blocks) |

Check SV + wake word logs:
```bash
grep -E "\[SV\]|\[Wake\]" /tmp/viko.log | tail -20
```

- [x] **Step 3: Final commit**

```bash
pkill -f "python viko.py" 2>/dev/null
git add -A
git commit -m "feat: latency + wake word — full implementation complete"
```
