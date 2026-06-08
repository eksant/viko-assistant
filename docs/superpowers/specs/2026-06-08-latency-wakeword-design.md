# Design: Latency Reduction + Wake Word ("Viko") Detection

**Date:** 2026-06-08  
**Status:** Approved  

---

## Problem

Two felt latency issues:

1. **Response latency (primary):** Speaker verification uses a 2-second input gate. Audio is buffered and replaced with silence bytes until resemblyzer confirms the owner's voice. After long silence periods, the first 1–3 utterances are dropped entirely, forcing the user to call "Viko" multiple times before getting a response.

2. **Playback latency (secondary):** `latency="high"` on `sd.RawOutputStream` adds 200–400ms of PortAudio ring-buffer delay.

3. **No wake word:** VIKO responds to everything. User wants it to only respond when addressed as "Viko".

---

## Goals

- VIKO responds to the **first** call of "Viko" — no repeated calling
- Response starts with minimum perceptible delay
- Only the enrolled owner's voice gets responses (speaker verification preserved)
- No new heavyweight dependencies (no Vosk, no Whisper)

---

## Non-Goals

- Sleep mode / hotword-only wakeup (Option B) — deferred
- Multi-turn conversation without repeating "Viko" per turn — out of scope for now

---

## Architecture

### Before

```
Mic → raw_queue → _verify_and_forward()
                  [2s buffer → resemblyzer → INPUT GATE]
                        ↓ verified         ↓ not verified
                   real audio            silence bytes
                        ↓
                   out_queue → Gemini Live
                                    ↓
                             response.data → audio_in_queue → Speaker
```

### After

```
Mic → Silero VAD → raw_queue → _verify_and_forward()
                               [no blocking, always forward real audio]
                                         ↓ background (speech chunks only)
                                    resemblyzer → self._sv_verified
                                         ↓
                               out_queue → Gemini Live

Gemini Live:
  sc.input_transcription → "viko" check → self._viko_addressed
  response.data → [OUTPUT GATE: _viko_addressed AND _sv_verified] → audio_in_queue → Speaker
  sc.turn_complete → reset _viko_addressed = False
```

---

## Components

### 1. Silero VAD (replaces RMS threshold)

**File:** `viko.py` — `_listen_audio()` and `VikoLive.__init__()`

- Install: `silero-vad` (ONNX runtime, ~2MB model, no PyTorch required)
- Init: `self._vad_model = load_silero_vad()` in `__init__` (ONNX mode auto-selected if torch absent)
- Per chunk (64ms): score audio, attach `is_speech: bool` to each queue item
- Threshold: `speech_prob > 0.5`
- Replaces: `SPEECH_THRESHOLD = 40` RMS check in `_verify_and_forward()`

**Why:** RMS threshold misses soft speech, especially after long silence when ambient noise is low. Silero VAD is a neural model trained specifically for speech activity; it handles mic warmup and quiet voices correctly.

### 2. Ungate Input — Speaker Verification Becomes Background

**File:** `viko.py` — `_verify_and_forward()`

- Remove silence-byte substitution: always put real audio into `out_queue`
- Keep resemblyzer running every ~1s, but only on chunks with `is_speech=True`
- Result stored in `self._sv_verified: bool` (default `True` — open until proven otherwise, same as current `verified_ok` default)
- Dual-threshold logic (pass=0.60, block=0.55) and recovery windows unchanged

**New state flag:** `self._sv_verified: bool = True` in `VikoLive.__init__()`

### 3. Wake Word Gate on Output

**File:** `viko.py` — `_receive_audio()`

Gemini Live sends `sc.input_transcription` (user's speech, streaming) **before** `response.data` (VIKO's audio). This ordering makes client-side wake word detection zero-cost in terms of latency.

- Maintain `self._viko_addressed: bool = False` in `__init__`
- When `sc.input_transcription.text` arrives: check if any of `["viko", "hei viko", "hey viko"]` in accumulated `in_buf` (case-insensitive)
- When `response.data` arrives: gate condition:
  ```python
  allowed = (
      self._viko_addressed
      and (self._sv_verified or self._verification_bypass or not self._sv.is_enrolled())
  )
  if allowed:
      self.audio_in_queue.put_nowait(response.data)
  # else: drop chunk silently — Gemini keeps streaming, VIKO stays silent
  ```
- On `turn_complete`: `self._viko_addressed = False`

**Why transcription, not system prompt:** System prompt instructions for Gemini to "stay silent" are unreliable — the model may still generate audio. Client-side gating is deterministic.

### 4. Output Latency Fix

**File:** `viko.py` — `_play_audio()` line 1380

```python
# Before:
latency="high"   # ~200–400ms PortAudio ring-buffer

# After:
latency="low"    # ~20–50ms
```

**Risk:** Under asyncio delays (e.g., during tool execution), audio may stutter. Acceptable trade-off since tool execution already interrupts natural speech flow anyway.

---

## New State Flags (VikoLive.__init__)

| Flag | Type | Default | Updated by |
|---|---|---|---|
| `_sv_verified` | `bool` | `True` | `_verify_and_forward()` background loop |
| `_viko_addressed` | `bool` | `False` | `_receive_audio()` on input_transcription |
| `_vad_model` | Silero model | loaded at init | — |

---

## Dependencies

Add to `requirements.txt`:
```
silero-vad>=5.1
```

No other new dependencies. Silero VAD's ONNX mode avoids adding PyTorch.

---

## Files Changed

| File | Change |
|---|---|
| `viko.py` | All four components above |
| `requirements.txt` | Add `silero-vad>=5.1` |

---

## Testing

1. **Wake word test:** Speak without saying "Viko" — VIKO should stay silent.
2. **Wake word test:** Say "Viko, cuaca hari ini?" — VIKO should respond normally.
3. **Speaker verification test:** With verification enabled, non-owner voice saying "Viko, ..." — VIKO should stay silent.
4. **Post-silence test:** After 60+ seconds of silence, say "Viko, halo" once — VIKO should respond on the first call.
5. **Playback latency:** Subjective — response should feel noticeably faster.
