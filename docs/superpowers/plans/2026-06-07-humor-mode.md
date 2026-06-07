# Humor Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `HUMOR MODE` section to VIKO's system prompt so that absurd/random humor fires on almost every response, with explicit off-switches for emotional, critical-technical, and religious contexts.

**Architecture:** Single prompt edit — insert new section between `KEPRIBADIAN` and `BIDANG KEAHLIAN` in `viko/prompt.txt`. No code changes required; VIKO auto-picks up the new prompt on next start.

**Tech Stack:** Plain text (`viko/prompt.txt`), Python process restart via shell.

---

### Task 1: Insert HUMOR MODE section into prompt

**Files:**
- Modify: `viko/prompt.txt` (after the KEPRIBADIAN block, before BIDANG KEAHLIAN)

- [ ] **Step 1: Locate insertion point**

Open `viko/prompt.txt`. Find the line that reads:

```
BIDANG KEAHLIAN:
```

The new section goes immediately before it, with one blank line separating from the previous block.

- [ ] **Step 2: Insert the section**

Insert this block immediately before `BIDANG KEAHLIAN:`:

```
HUMOR MODE:
- Gaya utama: absurd dan random. Analogi gila, perbandingan tak terduga,
  non-sequitur yang tetap nyambung konteks. Contoh: "ini kayak minta kucing
  ngajarin berenang — bisa, tapi butuh proses."
- Hampir tiap respons boleh ada sentuhan absurd — satu kalimat cukup.
  Prioritas tetap: task selesai dulu, humor jadi penutup atau bumbu.
- Boleh bikin analogi dari hal random (makanan, hewan, fisika kuantum, film B,
  dll) — asal relevan secara logika absurd.
- Tidak ada script baku — improvisasi bebas, tapi tetap singkat.

HUMOR OFF (wajib serius):
- Mode emosional/curhat: Eksa lagi down, butuh support → dengerin dulu,
  humor belakangan.
- Task teknis kritis: debug serius, error penting, self-engineer pipeline
  → fokus full, humor nanti.
- Topik agama/Al-Quran/Islam → tetap hormat, tidak ada celaan atau lelucon.

```

- [ ] **Step 3: Verify placement**

Run:
```bash
grep -n "HUMOR MODE\|BIDANG KEAHLIAN\|KEPRIBADIAN" viko/prompt.txt
```

Expected output (line numbers will differ, but order must be):
```
N:KEPRIBADIAN:
M:HUMOR MODE:
M+N:BIDANG KEAHLIAN:
```

`HUMOR MODE` must appear between `KEPRIBADIAN` and `BIDANG KEAHLIAN`.

- [ ] **Step 4: Commit**

```bash
git add viko/prompt.txt
git commit -m "feat: add absurd humor mode to VIKO personality"
```

---

### Task 2: Restart VIKO and verify

**Files:** None (runtime verification only)

- [ ] **Step 1: Kill running VIKO process**

```bash
pkill -f "python viko.py"
```

- [ ] **Step 2: Start VIKO**

```bash
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 5 && tail -5 /tmp/viko.log
```

Expected: process starts, DevTools line appears, no import errors.

- [ ] **Step 3: Manual smoke test**

Say or type a neutral, everyday question to VIKO (e.g. "apa kabar?" or "jam berapa sekarang?"). Verify the response includes at least one absurd/random analogy or non-sequitur touch — not just a plain factual reply.

- [ ] **Step 4: Verify HUMOR OFF**

Say something emotional (e.g. "lagi stress nih"). Verify VIKO responds with empathy first — no absurd humor.
