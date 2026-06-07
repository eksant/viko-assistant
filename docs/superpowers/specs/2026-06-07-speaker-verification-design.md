# Speaker Verification Design

**Date:** 2026-06-07
**Status:** Approved

---

## Goal

VIKO only responds to the owner's voice. Other speakers are silently ignored. Applies to both online mode (Gemini Live) and offline mode (faster-whisper).

---

## Library

**`resemblyzer>=0.1.1`** — offline, free, open source.
- Extracts a 256-dim speaker embedding from audio
- Cosine similarity to compare two embeddings
- Model ~50MB, loaded once into memory
- CPU-only, no GPU required

---

## Architecture

### New Component

**`viko/core/speaker_verifier.py`** — `SpeakerVerifier` class:

| Method | Signature | Description |
|---|---|---|
| `is_enrolled()` | `-> bool` | Check whether `memory/voice_profile.npy` exists |
| `enroll(pcm_bytes)` | `-> None` | Extract embedding from ~10s audio, save to disk |
| `similarity(pcm_bytes)` | `-> float` | Raw cosine similarity vs stored profile (0–1) |
| `verify(pcm_bytes)` | `-> bool` | True if similarity ≥ SIMILARITY_THRESHOLD |

Default threshold `0.65` — tight enough for a personal assistant, tolerant of mic variation and voice condition changes.

### Online Mode Pipeline Change

**Before:**
```
mic callback → out_queue → _send_realtime() → Gemini
```

**After:**
```
mic callback → raw_queue → _verify_and_forward() → out_queue → _send_realtime() → Gemini
```

`_verify_and_forward()` is a new async task in the TaskGroup:
- Read chunks from `raw_queue`
- Accumulate a 2-second verification window (VERIFY_CHUNKS = 32)
- Run `similarity()` in a thread executor every window
- Owner (score ≥ SV_PASS_THRESHOLD = 0.60) → forward real audio to `out_queue`
- Non-owner (score < SV_BLOCK_THRESHOLD = 0.55) → gate closed, send silence bytes to keep WebSocket alive
- Ambiguous (0.55–0.60) → maintain current gate state
- Silence window (RMS < SPEECH_THRESHOLD) → skip verification, maintain gate state

`_listen_audio()` sends to `raw_queue` via `loop.call_soon_threadsafe` (not directly to `out_queue`).

### Offline Mode Pipeline Change

Add a similarity check in `_offline_mode()` after VAD detects a completed utterance, before transcription:

```python
sim = await loop.run_in_executor(None, self._sv.similarity, pcm)
is_owner = (
    self._verification_bypass
    or not self._sv.is_enrolled()
    or sim >= SV_PASS_THRESHOLD
)
if not is_owner:
    buf, silence_count, speech_count, in_speech = [], 0, 0, False
    continue
```

### Bypass: Temporary Verification Disable

If `is_enrolled() == False` → `_verify_and_forward()` and `_offline_mode()` skip verification; all audio is forwarded. Active until enrollment completes.

---

## Enrollment Flow

**When:** After API key validation, before Gemini connect — part of the boot sequence.

**Flow:**
```
run() → check is_enrolled()
  → False:
      boot progress bar: "REGISTERING VOICE..."
      UI log: "SYS: Please speak freely for 10 seconds..."
      Record mic for 10 seconds (sounddevice directly, without Gemini)
      Progress bar updates every second (0% → 100%)
      Done → SpeakerVerifier.enroll(pcm_10s)
      UI log: "SYS: Voice successfully registered."
  → True: connect Gemini immediately
```

Owner can say anything during the 10 seconds — no specific phrase required.

**Re-enrollment:**
- Owner activates bypass via passphrase
- Type "Viko, kenali suaraku" in the text input
- `_on_text_command()` detects the phrase → triggers re-enrollment
- Old profile is overwritten

**Storage:** `memory/voice_profile.npy` — gitignored.

---

## Passphrase Bypass

Used when the owner is not recognized (illness, different mic, etc.).

**Setup:**
- `OWNER_PASSPHRASE` field in VIKO's initialization form (alongside `GEMINI_API_KEY`)
- Saved to `.env` as `OWNER_PASSPHRASE=...`
- If empty → passphrase bypass is disabled

**Flow:**
```
Owner types text in text input
  → _on_text_command() checks == OWNER_PASSPHRASE (before sending to Gemini)
  → Match:
      self._verification_bypass = True
      asyncio.get_event_loop().call_later(300, reset_bypass)
      UI log: "SYS: Bypass active for 5 minutes."
  → No match: text forwarded to Gemini as normal
```

While bypass is active: `_verify_and_forward()` skips gate, all audio goes to `out_queue`.

Passphrase is never sent to Gemini — checked and discarded in `_on_text_command()`.

---

## File Map

| Action | File | Description |
|---|---|---|
| Create | `viko/core/speaker_verifier.py` | SpeakerVerifier class |
| Modify | `requirements.txt` | Add `resemblyzer>=0.1.1` |
| Modify | `viko.py` | `__init__`, `run()` enrollment, `_listen_audio()`, `_verify_and_forward()`, `_offline_mode()`, passphrase in `_on_text_command()` |
| Modify | `viko/core/config.py` | Add `get_owner_passphrase()` |
| Modify | `viko/ui/window.py` | Add `OWNER_PASSPHRASE` field to initialization form |
| Modify | `.gitignore` | Add `memory/voice_profile.npy` |
| Modify | `CLAUDE.md` | Add `OWNER_PASSPHRASE` to env section, `speaker_verifier.py` to key files table |
| Modify | `README.md` | Add speaker verification to features, env vars, and architecture tree |

---

## Environment Variables

```env
OWNER_PASSPHRASE=...    # passphrase to bypass verification (empty = bypass disabled)
```

---

## VAD Constants

```python
SPEECH_THRESHOLD  = 300   # int16 RMS — speech detected
SILENCE_CHUNKS    = 20    # ~1.3s silence — utterance complete
MIN_SPEECH_CHUNKS = 8     # ~512ms minimum before verifying
```

---

## Dual-Threshold Gate (implemented)

| Score | Decision |
|---|---|
| ≥ 0.60 (SV_PASS_THRESHOLD) | Gate OPEN — verified owner |
| < 0.55 (SV_BLOCK_THRESHOLD) | Gate CLOSED — non-owner |
| 0.55–0.60 | Ambiguous — maintain current state |
| RMS < SPEECH_THRESHOLD | Silence — skip verification, maintain state |

Auto-recovery: after 5 consecutive ambiguous windows (~10s) while blocked, gate reopens (non-owner assumed gone).

---

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Library | resemblyzer | Free, offline, Python-native |
| Pipeline approach | Input gate (pre-Gemini) | Non-owner audio never reaches Gemini; handles short utterances correctly |
| Enrollment | Auto on first launch | Seamless UX, no manual setup |
| False-negative recovery | Typed passphrase | Reliable; avoids chicken-and-egg problem of voice PIN |
| Storage | `memory/voice_profile.npy` | Simple; no DB needed for a single owner |
| Scope | Online + offline mode | Consistent; non-owner cannot use VIKO in any mode |

---

## Out of Scope

- Multi-owner / trusted list (single owner sufficient for v1)
- Voice PIN (replaced by text passphrase)
- Speaker diarization (identifying who is speaking among multiple people)
- Cloud-based speaker ID
