# Speaker Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** VIKO hanya merespons suara owner — non-owner audio diabaikan diam-diam, baik online (Gemini Live) maupun offline (faster-whisper).

**Architecture:** Pre-buffer gate (Option A): mic audio masuk ke `raw_queue` → `_verify_and_forward()` kumpulkan utterance, verify speaker via resemblyzer, baru forward ke `out_queue` jika owner. Offline mode mendapat 3 baris verifikasi sebelum transcribe. Owner bisa bypass via typed passphrase (5 menit) atau re-enroll via teks command.

**Tech Stack:** `resemblyzer>=0.1.1` (speaker embeddings, ~50MB, offline/CPU), `numpy` (cosine similarity), `sounddevice` (enrollment recording), `PyQt6` (passphrase field).

---

## File Map

| Action | File | What changes |
|---|---|---|
| Create | `viko/core/speaker_verifier.py` | `SpeakerVerifier` class |
| Create | `tests/core/test_speaker_verifier.py` | 6 unit tests |
| Modify | `requirements.txt` | Add `resemblyzer>=0.1.1` |
| Modify | `viko/core/config.py` | Add `get_owner_passphrase()`, extend `save_keys()` |
| Modify | `viko/ui/window.py` | `SetupOverlay` 2nd field, signal `(str, str)`, `_on_api_key` saves passphrase |
| Modify | `viko.py` | `__init__` state, boot enrollment, passphrase+re-enroll in `_on_text_command`, `raw_queue` + `_verify_and_forward()`, offline verify |
| Modify | `.gitignore` | Add `memory/voice_profile.npy` |
| Modify | `CLAUDE.md` | Env table + key files table |
| Modify | `README.md` | Features, env vars, architecture tree |

---

## Task 1: Add resemblyzer dependency

**Files:**
- Modify: `requirements.txt`

- [x] **Step 1: Add resemblyzer to requirements.txt**

  In `requirements.txt`, after `faster-whisper>=1.2.1`:

  ```
  resemblyzer>=0.1.1
  ```

- [x] **Step 2: Install it**

  ```bash
  .venv/bin/pip install resemblyzer>=0.1.1
  ```

  Expected: package installs without errors. It downloads a pretrained encoder model (~50MB) on first use.

- [x] **Step 3: Verify import**

  ```bash
  .venv/bin/python -c "from resemblyzer import VoiceEncoder, preprocess_wav; print('ok')"
  ```

  Expected: `ok`

- [x] **Step 4: Commit**

  ```bash
  git add requirements.txt
  git commit -m "feat: add resemblyzer for speaker verification"
  ```

---

## Task 2: SpeakerVerifier class + tests

**Files:**
- Create: `viko/core/speaker_verifier.py`
- Create: `tests/core/test_speaker_verifier.py`

- [x] **Step 1: Write the failing tests**

  Create `tests/core/test_speaker_verifier.py`:

  ```python
  """Unit tests for viko.core.speaker_verifier.SpeakerVerifier (mocked resemblyzer)."""
  from unittest.mock import patch
  import numpy as np
  import tempfile
  import pytest
  from pathlib import Path

  from viko.core.speaker_verifier import SpeakerVerifier, SAMPLE_RATE, SIMILARITY_THRESHOLD


  def _make_pcm(seconds: float = 3.0) -> bytes:
      n = int(SAMPLE_RATE * seconds)
      return np.zeros(n, dtype=np.int16).tobytes()


  class TestSpeakerVerifier:
      def setup_method(self):
          self.tmp = tempfile.mkdtemp()
          self.profile = Path(self.tmp) / "voice_profile.npy"
          self.sv = SpeakerVerifier(profile_path=self.profile)

      def test_not_enrolled_initially(self):
          assert self.sv.is_enrolled() is False

      def test_enroll_creates_profile(self):
          fake_emb = np.ones(256, dtype=np.float64)
          with patch.object(self.sv, "_embed", return_value=fake_emb):
              self.sv.enroll(_make_pcm())
          assert self.profile.exists()

      def test_is_enrolled_after_enroll(self):
          fake_emb = np.ones(256, dtype=np.float64)
          with patch.object(self.sv, "_embed", return_value=fake_emb):
              self.sv.enroll(_make_pcm())
          assert self.sv.is_enrolled() is True

      def test_verify_returns_true_for_owner(self):
          emb = np.ones(256, dtype=np.float64)
          with patch.object(self.sv, "_embed", return_value=emb):
              self.sv.enroll(_make_pcm())
          with patch.object(self.sv, "_embed", return_value=emb):
              assert self.sv.verify(_make_pcm()) is True

      def test_verify_returns_false_for_stranger(self):
          owner_emb   = np.ones(256, dtype=np.float64)
          stranger_emb = -np.ones(256, dtype=np.float64)
          with patch.object(self.sv, "_embed", return_value=owner_emb):
              self.sv.enroll(_make_pcm())
          with patch.object(self.sv, "_embed", return_value=stranger_emb):
              assert self.sv.verify(_make_pcm()) is False

      def test_verify_returns_true_when_not_enrolled(self):
          # No profile → open access (enrollment not yet done)
          assert self.sv.verify(_make_pcm()) is True
  ```

- [x] **Step 2: Run tests to verify they fail**

  ```bash
  .venv/bin/python -m pytest tests/core/test_speaker_verifier.py -v
  ```

  Expected: `ModuleNotFoundError: No module named 'viko.core.speaker_verifier'`

- [x] **Step 3: Implement SpeakerVerifier**

  Create `viko/core/speaker_verifier.py`:

  ```python
  from __future__ import annotations
  import numpy as np
  from pathlib import Path

  SAMPLE_RATE         = 16000
  SIMILARITY_THRESHOLD = 0.75
  _PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "memory" / "voice_profile.npy"


  class SpeakerVerifier:
      def __init__(self, profile_path: Path = _PROFILE_PATH) -> None:
          self._path    = profile_path
          self._encoder = None

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
          return self._path.exists()

      def enroll(self, pcm_bytes: bytes) -> None:
          embedding = self._embed(pcm_bytes)
          self._path.parent.mkdir(parents=True, exist_ok=True)
          np.save(str(self._path), embedding)

      def verify(self, pcm_bytes: bytes) -> bool:
          if not self.is_enrolled():
              return True
          stored    = np.load(str(self._path))
          candidate = self._embed(pcm_bytes)
          similarity = float(
              np.dot(stored, candidate)
              / (np.linalg.norm(stored) * np.linalg.norm(candidate))
          )
          return similarity >= SIMILARITY_THRESHOLD
  ```

- [x] **Step 4: Run tests to verify they pass**

  ```bash
  .venv/bin/python -m pytest tests/core/test_speaker_verifier.py -v
  ```

  Expected: `6 passed`

- [x] **Step 5: Commit**

  ```bash
  git add viko/core/speaker_verifier.py tests/core/test_speaker_verifier.py
  git commit -m "feat: add SpeakerVerifier with resemblyzer embeddings and tests"
  ```

---

## Task 3: Config — `get_owner_passphrase()` + extend `save_keys()`

**Files:**
- Modify: `viko/core/config.py:49-60`

- [x] **Step 1: Add `get_owner_passphrase()` after `get_openrouter_key()`**

  In `viko/core/config.py`, after `get_openrouter_key()` (currently ends around line 37), add:

  ```python
  def get_owner_passphrase() -> str:
      return os.environ.get("OWNER_PASSPHRASE", "").strip()
  ```

- [x] **Step 2: Add `owner_passphrase` parameter to `save_keys()`**

  Replace the current `save_keys` signature and body (lines 49–60):

  ```python
  def save_keys(
      gemini_api_key: str = "",
      openrouter_api_key: str = "",
      os_system: str = "",
      owner_passphrase: str = "",
  ) -> None:
      data = _load_env_dict()
      if gemini_api_key.strip():
          data["GEMINI_API_KEY"] = gemini_api_key.strip()
          os.environ["GEMINI_API_KEY"] = gemini_api_key.strip()
      if openrouter_api_key.strip():
          data["OPENROUTER_API_KEY"] = openrouter_api_key.strip()
          os.environ["OPENROUTER_API_KEY"] = openrouter_api_key.strip()
      if os_system.strip():
          data["OS_SYSTEM"] = os_system.strip()
          os.environ["OS_SYSTEM"] = os_system.strip()
      if owner_passphrase.strip():
          data["OWNER_PASSPHRASE"] = owner_passphrase.strip()
          os.environ["OWNER_PASSPHRASE"] = owner_passphrase.strip()
      _write_env_dict(data)
  ```

- [x] **Step 3: Verify no syntax errors**

  ```bash
  .venv/bin/python -c "from viko.core.config import get_owner_passphrase, save_keys; print('ok')"
  ```

  Expected: `ok`

- [x] **Step 4: Commit**

  ```bash
  git add viko/core/config.py
  git commit -m "feat: add get_owner_passphrase() and owner_passphrase to save_keys()"
  ```

---

## Task 4: UI form — OWNER_PASSPHRASE field in SetupOverlay

**Files:**
- Modify: `viko/ui/window.py:79-124` (SetupOverlay class)
- Modify: `viko/ui/window.py:33` (imports)
- Modify: `viko/ui/window.py:606-612` (`_on_api_key` handler)

- [x] **Step 1: Add `save_keys` to the config import in window.py**

  Line 33 currently:
  ```python
  from viko.core.config import is_configured, get_gemini_key
  ```

  Change to:
  ```python
  from viko.core.config import is_configured, get_gemini_key, save_keys
  ```

- [x] **Step 2: Change `done` signal to emit two strings**

  Line 81 currently:
  ```python
  done = pyqtSignal(str)   # emits gemini_api_key
  ```

  Change to:
  ```python
  done = pyqtSignal(str, str)   # emits (gemini_api_key, owner_passphrase)
  ```

- [x] **Step 3: Add OWNER_PASSPHRASE field to the form**

  After the existing `lay.addWidget(self._key, ...)` block (currently line 107) and before the button, insert:

  ```python
        lbl2 = QLabel("Owner Passphrase (bypass verifikasi suara)")
        lbl2.setFont(F(9)); lbl2.setStyleSheet(f"color: {TXT.name()};")
        lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl2)

        self._pass = QLineEdit(); self._pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass.setFont(F(9)); self._pass.setFixedWidth(360)
        self._pass.setPlaceholderText("Kosongkan jika tidak digunakan")
        self._pass.setStyleSheet("""
            QLineEdit { background: #010d14; color: #8ffcff;
                        border: 1px solid #0d3347; border-radius: 4px; padding: 8px; }
            QLineEdit:focus { border-color: #00d4ff; }
        """)
        lay.addWidget(self._pass, alignment=Qt.AlignmentFlag.AlignCenter)
  ```

  Also connect `self._pass.returnPressed` to `self._submit` (add alongside the existing `self._key.returnPressed.connect(self._submit)`):
  ```python
        self._pass.returnPressed.connect(self._submit)
  ```

- [x] **Step 4: Update `_submit()` to emit both values**

  Replace current `_submit()` (lines 120–123):

  ```python
      def _submit(self):
          key = self._key.text().strip()
          if key:
              self.done.emit(key, self._pass.text().strip())
  ```

- [x] **Step 5: Update `_on_api_key` to accept and save passphrase**

  Replace current `_on_api_key` (lines 606–612):

  ```python
      def _on_api_key(self, key: str, passphrase: str):
          save_keys(gemini_api_key=key, owner_passphrase=passphrase)
          self._ready = True
          if self._overlay:
              self._overlay.hide(); self._overlay = None
          self._apply_state("LISTENING")
          self._activity.append_log("SYS: Initialised. Viko online.")
  ```

- [x] **Step 6: Verify no syntax errors**

  ```bash
  .venv/bin/python -c "from viko.ui.window import MainWindow; print('ok')"
  ```

  Expected: `ok` (Qt may need a display but import should succeed)

- [x] **Step 7: Commit**

  ```bash
  git add viko/ui/window.py
  git commit -m "feat: add OWNER_PASSPHRASE field to setup form and persist to .env"
  ```

---

## Task 5: Boot-time enrollment in `run()`

**Files:**
- Modify: `viko.py:620-636` (`__init__` additions)
- Modify: `viko.py:1257-1270` (`run()` before while loop)

- [x] **Step 1: Import SpeakerVerifier and get_owner_passphrase at top of viko.py**

  After the existing `from viko.core.logger import get_logger` import (line 26), add:

  ```python
  from viko.core.speaker_verifier import SpeakerVerifier
  ```

  `get_owner_passphrase` will be lazy-imported inline (same pattern as `get_gemini_key`).

- [x] **Step 2: Add state fields to `VikoLive.__init__`**

  In `__init__` (after `self._offline_stt = None` on line 634), add:

  ```python
          self._sv                  = SpeakerVerifier()
          self._verification_bypass = False
          self._enrolling           = False
          self._enroll_buf: list    = []
          self._enroll_target: int  = 0
          self.raw_queue            = None
  ```

- [x] **Step 3: Add `_enroll_voice()` async method to VikoLive**

  Add this method after `_warmup_offline_stt()` (around line 688):

  ```python
      async def _enroll_voice(self) -> None:
          """Record 10 seconds of mic audio and save owner voice profile."""
          loop = asyncio.get_running_loop()
          audio_q: asyncio.Queue = asyncio.Queue()

          def _cb(indata, frames, time_info, status):
              loop.call_soon_threadsafe(audio_q.put_nowait, indata.tobytes())

          target = int(10 * SEND_SAMPLE_RATE / CHUNK_SIZE)  # ~156 chunks = 10s
          chunks = []

          with sd.InputStream(
              samplerate=SEND_SAMPLE_RATE,
              channels=CHANNELS,
              dtype="int16",
              blocksize=CHUNK_SIZE,
              callback=_cb,
          ):
              for i in range(target):
                  chunk = await audio_q.get()
                  chunks.append(chunk)

          pcm = b"".join(chunks)
          await loop.run_in_executor(None, self._sv.enroll, pcm)
  ```

- [x] **Step 4: Add enrollment step in `run()` before the while loop**

  In `run()` after `self.ui.set_boot_progress(0.35, "BUILDING CONTEXT...")` (line 1266) and before `_first_connect = True` (line 1269), insert:

  ```python
          # Enrollment: first launch (no voice profile yet)
          if not self._sv.is_enrolled():
              self.ui.set_boot_progress(0.45, "MENDAFTARKAN SUARA...")
              self.ui.write_log("SYS: Silakan berbicara bebas selama 10 detik...")
              await self._enroll_voice()
              self.ui.write_log("SYS: Suara berhasil didaftarkan.")
  ```

- [x] **Step 5: Verify no syntax errors**

  ```bash
  .venv/bin/python -c "import viko; print('ok')"
  ```

  Expected: `ok`

- [x] **Step 6: Commit**

  ```bash
  git add viko.py
  git commit -m "feat: add boot-time voice enrollment before Gemini session"
  ```

---

## Task 6: Passphrase bypass + re-enrollment trigger in `_on_text_command()`

**Files:**
- Modify: `viko.py:638-657` (`_on_text_command`)

- [x] **Step 1: Add `_start_re_enrollment()` async method to VikoLive**

  Add after `_enroll_voice()`:

  ```python
      async def _start_re_enrollment(self) -> None:
          """Signal _verify_and_forward() to collect 10s of audio for re-enrollment."""
          self.ui.write_log("SYS: Silakan berbicara bebas selama 10 detik untuk mendaftarkan suara baru...")
          self._enroll_buf    = []
          self._enroll_target = int(10 * SEND_SAMPLE_RATE / CHUNK_SIZE)
          self._enrolling     = True
  ```

- [x] **Step 2: Update `_on_text_command()` to check passphrase and re-enrollment phrase**

  Replace the current body of `_on_text_command()` (lines 638–657):

  ```python
      def _on_text_command(self, text: str):
          if self.ui.paused:
              return
          self.ui.write_log(f"YOU: {text}")

          # Passphrase bypass — check before forwarding to Gemini
          from viko.core.config import get_owner_passphrase
          passphrase = get_owner_passphrase()
          if passphrase and text.strip() == passphrase:
              def _reset_bypass():
                  self._verification_bypass = False
                  self.ui.write_log("SYS: Bypass verifikasi suara nonaktif.")
              self._verification_bypass = True
              if self._loop:
                  self._loop.call_later(300, _reset_bypass)
              self.ui.write_log("SYS: Bypass aktif 5 menit.")
              return  # never sent to Gemini

          # Re-enrollment phrase — requires bypass active
          if text.strip().lower() == "viko, kenali suaraku" and self._verification_bypass:
              if self._loop:
                  asyncio.run_coroutine_threadsafe(
                      self._start_re_enrollment(), self._loop
                  )
              return  # never sent to Gemini

          if not self._loop or not self.session:
              self.ui.write_log("SYS: Session not ready — try again in a moment.")
              return
          fut = asyncio.run_coroutine_threadsafe(
              self.session.send_client_content(
                  turns={"role": "user", "parts": [{"text": text}]},
                  turn_complete=True,
              ),
              self._loop,
          )
          def _on_done(f):
              try:
                  f.result()
              except Exception as exc:
                  self.ui.write_log(f"ERR: text send failed — {exc}")
          fut.add_done_callback(_on_done)
  ```

- [x] **Step 3: Verify no syntax errors**

  ```bash
  .venv/bin/python -c "import viko; print('ok')"
  ```

  Expected: `ok`

- [x] **Step 4: Commit**

  ```bash
  git add viko.py
  git commit -m "feat: add passphrase bypass and re-enrollment trigger in _on_text_command"
  ```

---

## Task 7: Pre-buffer gate — `raw_queue` + `_verify_and_forward()`

**Files:**
- Modify: `viko.py:1283-1330` (`run()` — queue init + TaskGroup)
- Modify: `viko.py:1075-1106` (`_listen_audio()`)
- Add: new method `_verify_and_forward()` in VikoLive

- [x] **Step 1: Initialize `raw_queue` in `run()` alongside `out_queue`**

  In `run()`, find where `out_queue` is initialized (line ~1286):
  ```python
  self.out_queue = asyncio.Queue(maxsize=10)
  ```

  Add `raw_queue` initialization immediately after:
  ```python
  self.raw_queue = asyncio.Queue(maxsize=200)
  ```

- [x] **Step 2: Add `_verify_and_forward()` as 6th task in TaskGroup**

  After `tg.create_task(self._session_watchdog())` (line 1330), add:
  ```python
                  tg.create_task(self._verify_and_forward())
  ```

- [x] **Step 3: Change `_listen_audio()` to send to `raw_queue`**

  In `_listen_audio()` callback (lines 1083–1091), change `self.out_queue` to `self.raw_queue`:

  ```python
      async def _listen_audio(self):
          try:
              dev = sd.query_devices(kind='input')
              print(f"[Viko] Mic: {dev['name']} @ {SEND_SAMPLE_RATE}Hz")
          except Exception:
              print("[Viko] Mic started")
          loop = asyncio.get_event_loop()

          def callback(indata, frames, time_info, status):
              with self._speaking_lock:
                  viko_speaking = self._is_speaking
              if viko_speaking or self.ui.muted or self.ui.paused:
                  return
              loop.call_soon_threadsafe(
                  self.raw_queue.put_nowait,
                  {"data": indata.tobytes(), "mime_type": "audio/pcm"}
              )

          try:
              with sd.InputStream(
                  samplerate=SEND_SAMPLE_RATE,
                  channels=CHANNELS,
                  dtype="int16",
                  blocksize=CHUNK_SIZE,
                  callback=callback,
              ):
                  print("[Viko] Mic stream open")
                  while True:
                      await asyncio.sleep(0.1)
          except Exception as e:
              print(f"[Viko] Mic error: {e}")
              raise
  ```

- [x] **Step 4: Implement `_verify_and_forward()`**

  Add this method after `_listen_audio()`:

  ```python
      async def _verify_and_forward(self):
          """VAD gate: collect utterances from raw_queue, verify speaker, forward to out_queue.

          Also handles in-session re-enrollment when self._enrolling is True.
          """
          SPEECH_THRESHOLD  = 300
          SILENCE_CHUNKS    = 20
          MIN_SPEECH_CHUNKS = 8

          loop = asyncio.get_running_loop()
          buf:           list[dict] = []
          silence_count: int  = 0
          speech_count:  int  = 0
          in_speech:     bool = False

          while True:
              item        = await self.raw_queue.get()
              chunk_bytes = item["data"]

              # Re-enrollment mode: collect audio, skip normal VAD
              if self._enrolling:
                  self._enroll_buf.append(item)
                  if len(self._enroll_buf) >= self._enroll_target:
                      self._enrolling = False
                      pcm = b"".join(i["data"] for i in self._enroll_buf)
                      self._enroll_buf = []
                      await loop.run_in_executor(None, self._sv.enroll, pcm)
                      self.ui.write_log("SYS: Suara berhasil didaftarkan.")
                  continue

              rms = _rms(chunk_bytes)

              if rms > SPEECH_THRESHOLD:
                  buf.append(item)
                  speech_count += 1
                  silence_count = 0
                  in_speech = True
              elif in_speech:
                  buf.append(item)
                  silence_count += 1
                  if silence_count >= SILENCE_CHUNKS:
                      if speech_count >= MIN_SPEECH_CHUNKS:
                          pcm = b"".join(i["data"] for i in buf)
                          is_owner = (
                              self._verification_bypass
                              or not self._sv.is_enrolled()
                              or await loop.run_in_executor(
                                  None, self._sv.verify, pcm
                              )
                          )
                          if is_owner:
                              for i in buf:
                                  await self.out_queue.put(i)
                      buf           = []
                      silence_count = 0
                      speech_count  = 0
                      in_speech     = False
  ```

- [x] **Step 5: Verify no syntax errors**

  ```bash
  .venv/bin/python -c "import viko; print('ok')"
  ```

  Expected: `ok`

- [x] **Step 6: Run full test suite to confirm no regressions**

  ```bash
  .venv/bin/python -m pytest tests/ -v
  ```

  Expected: all tests pass.

- [x] **Step 7: Commit**

  ```bash
  git add viko.py
  git commit -m "feat: add pre-buffer gate _verify_and_forward() with raw_queue pipeline"
  ```

---

## Task 8: Offline mode speaker verification

**Files:**
- Modify: `viko.py:776-785` (inside `_offline_mode()` VAD block)

- [x] **Step 1: Add verify block before transcribe in `_offline_mode()`**

  In `_offline_mode()`, the utterance-complete block currently reads (around lines 776–785):

  ```python
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
  ```

  Change it to add speaker verification before transcribing:

  ```python
                      if silence_count >= SILENCE_CHUNKS:
                          if speech_count >= MIN_SPEECH_CHUNKS:
                              pcm = b"".join(buf)
                              is_owner = (
                                  self._verification_bypass
                                  or not self._sv.is_enrolled()
                                  or await loop.run_in_executor(
                                      None, self._sv.verify, pcm
                                  )
                              )
                              if is_owner:
                                  text = await loop.run_in_executor(
                                      None, stt.transcribe_pcm, pcm
                                  )
                                  if text.strip():
                                      self.ui.write_log(f"You [offline]: {text}")
                                      await self._offline_respond(text)
                          buf           = []
                          silence_count = 0
                          speech_count  = 0
                          in_speech     = False
  ```

- [x] **Step 2: Verify no syntax errors**

  ```bash
  .venv/bin/python -c "import viko; print('ok')"
  ```

  Expected: `ok`

- [x] **Step 3: Run full test suite**

  ```bash
  .venv/bin/python -m pytest tests/ -v
  ```

  Expected: all tests pass.

- [x] **Step 4: Commit**

  ```bash
  git add viko.py
  git commit -m "feat: add speaker verification to offline mode VAD loop"
  ```

---

## Task 9: Gitignore, CLAUDE.md, README.md

**Files:**
- Modify: `.gitignore`
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [x] **Step 1: Add voice profile to .gitignore**

  In `.gitignore`, after `memory/*.sqlite3` block, add:

  ```
  memory/voice_profile.npy
  ```

- [x] **Step 2: Update CLAUDE.md — env section**

  In `CLAUDE.md` under the `## Environment` code block, add after `CAMERA_INDEX=0`:

  ```
  OWNER_PASSPHRASE=...     # optional — typed bypass for speaker verification (empty = bypass off)
  ```

- [x] **Step 3: Update CLAUDE.md — key files table**

  In `CLAUDE.md` under `## Key Files`, add a row after `viko/core/memory.py`:

  ```
  | `viko/core/speaker_verifier.py` | Speaker embedding, enroll, verify (resemblyzer) |
  ```

  Also add `memory/voice_profile.npy` to the **What NOT to Do** section:
  ```
  - Do not commit `.env`, `memory/*.db`, `memory/*.sqlite3`, `memory/voice_profile.npy`, or `workspace/` files
  ```

- [x] **Step 4: Update README.md**

  Locate the features list and add speaker verification. Locate the environment variables section and add `OWNER_PASSPHRASE`. If there's an architecture/file tree section, add `viko/core/speaker_verifier.py`.

  (The exact lines depend on current README content — make minimal additions consistent with existing style.)

- [x] **Step 5: Verify .gitignore is correct**

  ```bash
  git check-ignore -v memory/voice_profile.npy
  ```

  Expected: `.gitignore:XX:memory/voice_profile.npy    memory/voice_profile.npy`

- [x] **Step 6: Commit**

  ```bash
  git add .gitignore CLAUDE.md README.md
  git commit -m "docs: add speaker verification to gitignore, CLAUDE.md, README"
  ```

---

## Self-Review

### Spec coverage check

| Spec requirement | Covered by |
|---|---|
| resemblyzer library | Task 1 |
| SpeakerVerifier: is_enrolled, enroll, verify | Task 2 |
| SIMILARITY_THRESHOLD = 0.75 | Task 2 (constant in speaker_verifier.py) |
| pre-buffer gate: raw_queue → _verify_and_forward → out_queue | Task 7 |
| VAD constants: SPEECH_THRESHOLD=300, SILENCE_CHUNKS=20, MIN_SPEECH_CHUNKS=8 | Task 7 |
| Enrollment on first launch (before Gemini connect) | Task 5 |
| OWNER_PASSPHRASE in setup form | Task 4 |
| OWNER_PASSPHRASE saved to .env via save_keys() | Task 3 + 4 |
| Passphrase bypass — 5 minutes, checked before Gemini | Task 6 |
| Re-enrollment via "Viko, kenali suaraku" | Task 6 + 7 |
| Offline mode verification | Task 8 |
| memory/voice_profile.npy gitignored | Task 9 |
| Not enrolled → open access (bypass gate) | Task 2 (verify returns True), Task 7 (is_enrolled check) |
| CLAUDE.md + README.md updated | Task 9 |

### Placeholder scan

No TBD or TODO items. All code blocks are complete and self-contained.

### Type consistency

- `SpeakerVerifier.enroll(pcm_bytes: bytes)` — used in Task 5 `_enroll_voice()` and Task 7 `_verify_and_forward()` ✓
- `SpeakerVerifier.verify(pcm_bytes: bytes) -> bool` — used in Task 7 and Task 8 ✓
- `SpeakerVerifier.is_enrolled() -> bool` — used in Task 5 and Task 7 and Task 8 ✓
- `self._sv` — created in Task 5, used in Tasks 6, 7, 8 ✓
- `self._verification_bypass` — created in Task 5 `__init__`, set in Task 6, read in Tasks 7, 8 ✓
- `self._enrolling`, `self._enroll_buf`, `self._enroll_target` — created in Task 5 `__init__`, set in Task 6 `_start_re_enrollment()`, consumed in Task 7 `_verify_and_forward()` ✓
- `self.raw_queue` — init to `None` in Task 5 `__init__`, assigned in Task 7 `run()`, used in `_listen_audio()` and `_verify_and_forward()` ✓
- `done = pyqtSignal(str, str)` — changed in Task 4, emitted with `(key, passphrase)` in Task 4, connected to `_on_api_key(self, key, passphrase)` in Task 4 ✓
