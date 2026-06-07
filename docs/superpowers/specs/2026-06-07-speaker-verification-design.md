# Speaker Verification Design

**Date:** 2026-06-07
**Status:** Approved

---

## Goal

VIKO hanya merespon suara owner. Orang lain yang berbicara ke VIKO diabaikan secara diam-diam (silent ignore). Berlaku di online mode (Gemini Live) dan offline mode (faster-whisper).

---

## Library

**`resemblyzer>=0.1.1`** — offline, free, open source.
- Extract 256-dim speaker embedding dari audio
- Cosine similarity untuk membandingkan dua embedding
- Model ~50MB, load sekali di memory
- Tidak butuh GPU, berjalan di CPU

---

## Architecture

### Komponen Baru

**`viko/core/speaker_verifier.py`** — `SpeakerVerifier` class:

| Method | Signature | Deskripsi |
|---|---|---|
| `is_enrolled()` | `-> bool` | Cek apakah `memory/voice_profile.npy` ada |
| `enroll(pcm_bytes)` | `-> None` | Extract embedding dari ~10s audio, simpan ke disk |
| `verify(pcm_bytes)` | `-> bool` | Cosine similarity vs stored profile, True jika ≥ 0.75 |

Threshold default `0.75` — cukup ketat untuk personal assistant, toleran terhadap variasi mic dan kondisi suara.

### Perubahan Pipeline Online Mode

**Sebelum:**
```
mic callback → out_queue → _send_realtime() → Gemini
```

**Setelah:**
```
mic callback → raw_queue → _verify_and_forward() → out_queue → _send_realtime() → Gemini
```

`_verify_and_forward()` adalah async task baru di TaskGroup:
- Baca chunks dari `raw_queue`
- VAD buffer (energy RMS threshold 300, silence 20 chunks, min speech 8 chunks)
- Utterance selesai → `verify()` di thread executor
- Owner (score ≥ 0.75) → drain buffer ke `out_queue`
- Non-owner → clear buffer, diam

`_listen_audio()` callback diubah: kirim ke `raw_queue` (bukan langsung `out_queue`).

### Perubahan Pipeline Offline Mode

Tambah 3 baris di `_offline_mode()` setelah VAD detect utterance selesai, sebelum transcribe:

```python
if not self._sv.verify(pcm):
    buf, silence_count, speech_count, in_speech = [], 0, 0, False
    continue
```

### Bypass: Verification dinonaktifkan sementara

Kalau `is_enrolled() == False` → `_verify_and_forward()` dan `_offline_mode()` skip verification, semua audio diteruskan. Aktif sampai enrollment selesai.

---

## Enrollment Flow

**Kapan:** Setelah API key valid, sebelum Gemini connect — bagian dari boot sequence.

**Flow:**
```
run() → cek is_enrolled()
  → False:
      boot progress bar: "MENDAFTARKAN SUARA..."
      UI log: "SYS: Silakan berbicara bebas selama 10 detik..."
      Rekam mic 10 detik (sounddevice langsung, tanpa Gemini)
      Progress bar update setiap detik (0% → 100%)
      Selesai → SpeakerVerifier.enroll(pcm_10s)
      UI log: "SYS: Suara berhasil didaftarkan."
  → True: langsung connect Gemini
```

Owner bisa ngomong apa saja selama 10 detik — tidak perlu kata tertentu.

**Re-enrollment:**
- Owner aktifkan bypass via passphrase
- Ketik "Viko, kenali suaraku" di text input
- `_on_text_command()` deteksi phrase → trigger enrollment ulang
- Profile lama ditimpa

**Storage:** `memory/voice_profile.npy` — gitignored.

---

## Passphrase Bypass

Digunakan saat owner tidak dikenali (sakit, mic berbeda, dll).

**Setup:**
- Field `OWNER_PASSPHRASE` di form inisialisasi VIKO (bersama `GEMINI_API_KEY`)
- Disimpan ke `.env` sebagai `OWNER_PASSPHRASE=...`
- Jika kosong → bypass via passphrase dinonaktifkan

**Flow:**
```
Owner ketik teks di text input
  → _on_text_command() cek == OWNER_PASSPHRASE (sebelum kirim ke Gemini)
  → Cocok:
      self._verification_bypass = True
      asyncio.get_event_loop().call_later(300, reset_bypass)
      UI log: "SYS: Bypass aktif 5 menit."
  → Tidak cocok: teks diteruskan ke Gemini seperti biasa
```

Selama bypass aktif: `_verify_and_forward()` skip gate, semua audio ke `out_queue`.

Passphrase tidak pernah dikirim ke Gemini — dicek dan dibuang di `_on_text_command()`.

---

## File Map

| Action | File | Deskripsi |
|---|---|---|
| Create | `viko/core/speaker_verifier.py` | SpeakerVerifier class |
| Modify | `requirements.txt` | Tambah `resemblyzer>=0.1.1` |
| Modify | `viko.py` | `__init__`, `run()` enrollment, `_listen_audio()`, `_verify_and_forward()`, `_offline_mode()`, passphrase di `_on_text_command()` |
| Modify | `viko/core/config.py` | Tambah `get_owner_passphrase()` |
| Modify | `viko/ui/window.py` | Tambah field `OWNER_PASSPHRASE` di form inisialisasi |
| Modify | `.gitignore` | Tambah `memory/voice_profile.npy` |
| Modify | `CLAUDE.md` | Tambah `OWNER_PASSPHRASE` ke env section, `speaker_verifier.py` ke key files table |
| Modify | `README.md` | Tambah speaker verification ke features, env vars, dan architecture tree |

---

## Environment Variables

```env
OWNER_PASSPHRASE=...    # passphrase untuk bypass verifikasi (kosong = bypass nonaktif)
```

---

## VAD Constants (sama dengan offline mode)

```python
SPEECH_THRESHOLD  = 300   # int16 RMS — mulai bicara
SILENCE_CHUNKS    = 20    # ~1.3s diam — utterance selesai
MIN_SPEECH_CHUNKS = 8     # ~512ms minimum untuk verify
```

---

## Keputusan Desain

| Keputusan | Pilihan | Alasan |
|---|---|---|
| Library | resemblyzer | Free, offline, Python native |
| Pipeline approach | Option A (pre-buffer gate) | Non-owner audio tidak pernah sampai ke Gemini; handle utterance pendek dengan benar |
| Enrollment | Auto saat first launch | UX paling seamless, tidak perlu manual setup |
| False negative recovery | Typed passphrase | Reliable, tidak ada chicken-and-egg problem seperti voice PIN |
| Storage | `memory/voice_profile.npy` | Simple, tidak perlu DB untuk satu owner |
| Scope | Online + offline mode | Konsisten, non-owner tidak bisa pakai VIKO mode apapun |

---

## Out of Scope

- Multi-owner / trusted list (satu owner cukup untuk v1)
- Voice PIN (diganti passphrase teks)
- Speaker diarization (siapa yang bicara saat ada banyak orang)
- Cloud-based speaker ID
