# Design: VIKO Humor Mode

**Date:** 2026-06-07
**Status:** Approved

## Problem

VIKO's current personality already permits light humor (sarkasme halus, slang gaul), but the rules are vague and undersell the absurd/random humor style the owner wants. There is no guidance on style, frequency, or hard-off conditions, so humor ends up inconsistent.

## Goal

Add a dedicated `HUMOR MODE` section to `viko/prompt.txt` that gives VIKO clear permission and style guidance for absurd/random humor — while explicitly defining the three contexts where humor must be suppressed.

## Approach

Append a new section called `HUMOR MODE` directly after the existing `KEPRIBADIAN` section in `viko/prompt.txt`. No code changes required — prompt edit only.

## Design

### New section content

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

### Placement

Inserted between `KEPRIBADIAN` and `BIDANG KEAHLIAN` sections.

## Constraints

- Prompt-only change — zero code impact
- Existing humor rules in `KEPRIBADIAN` remain; `HUMOR MODE` extends them
- All 24 self-engineer tests unaffected (no code changed)

## Out of Scope

- No new tools or skills
- No UI changes
- No change to voice agent routing
