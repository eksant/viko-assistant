# VIKO SelfEngineer Pipeline — Design Spec
**Date:** 2026-06-07  
**Status:** Approved

---

## Overview

VIKO dapat memodifikasi kodenya sendiri ketika diperintahkan lewat suara. Ini mencakup: menambah skill baru, memperbaiki bug, mengubah perilaku/prompt, memodifikasi UI, dan me-restore perubahan. Pendekatan menggunakan pipeline state machine (SelfEngineer) dengan konfirmasi user di dua titik kritis: sebelum eksekusi dan sebelum restart.

---

## Scope Modifikasi

- **Semua file VIKO** boleh dimodifikasi (skills, prompt, config, memory, UI, core)
- **Safety**: backup wajib sebelum satu byte pun diubah
- **Versioning**: file-based dulu (backup + manifest), git-based setelah sistem terbukti stabil

---

## Arsitektur Modul

```
viko/
  self_engineer/
    __init__.py
    engine.py       ← orchestrator utama (state machine)
    analyzer.py     ← baca & pahami codebase VIKO
    planner.py      ← Gemini generate structured plan
    generator.py    ← generate code changes/patches
    backup.py       ← file versioning & restore
    tester.py       ← syntax + import + smoke test
    restarter.py    ← graceful restart VIKO
    backups/        ← folder backup (auto-created, gitignored)

viko/skills/
  self_update.py    ← voice-facing skill, wrap engine.py
```

---

## State Machine

```
ANALYZE → PLAN → [user confirm] → GENERATE → BACKUP → APPLY → TEST → [user confirm restart] → RESTART
                      ↑ cancel                                              ↑ skip / rollback
```

**States:**
| State | Deskripsi |
|---|---|
| ANALYZE | Scan file relevan berdasarkan intent |
| PLAN | Gemini buat structured plan + announce ke user |
| USER_CONFIRM_PLAN | Tunggu konfirmasi user ("lanjutkan?") |
| GENERATE | Gemini generate actual code changes |
| BACKUP | Simpan originals + catat ke manifest |
| APPLY | Tulis perubahan ke disk |
| TEST | Syntax + import + smoke test di subprocess |
| USER_CONFIRM_RESTART | Announce hasil test + tanya restart |
| RESTART | Graceful restart VIKO |
| ROLLBACK | Restore dari backup (jika test FAIL atau user cancel) |

---

## Komponen Detail

### analyzer.py

Tujuan: bangun context paket yang cukup untuk Planner tanpa banjir token.

```
Input: intent string + optional target_files
Output: {files: {path: content}, structure_summary, intent_category}

Logic:
  - Baca manifest VIKO (semua file + ukuran + deskripsi singkat)
  - Identifikasi file relevan berdasarkan intent:
      "skill baru"  → baca 1-2 skill existing sebagai template
      "fix bug"     → baca file yang disebutkan + recent error context
      "ubah prompt" → baca prompt.txt saja
      "ubah UI"     → baca ui.py + ui_widgets.py header
  - Token budget: maksimal ~20K tokens untuk context paket
```

### planner.py

Tujuan: hasilkan structured plan yang bisa diumumkan ke user dan dieksekusi oleh generator.

```json
{
  "intent": "Tambah skill crypto price",
  "summary_for_voice": "Saya akan membuat file baru crypto_price.py dan mendaftarkannya di viko.py.",
  "changes": [
    {
      "action": "create",
      "file": "viko/skills/crypto_price.py",
      "description": "Skill baru: ambil harga crypto dari CoinGecko API"
    },
    {
      "action": "modify",
      "file": "viko.py",
      "targets": ["import section", "TOOL_DECLARATIONS"],
      "description": "Daftarkan skill crypto_price"
    }
  ],
  "test_strategy": ["syntax", "import", "mock_call"]
}
```

### generator.py

Tujuan: hasilkan content aktual untuk setiap change dalam plan.

```
Untuk "create" → generate full file content
Untuk "modify" → generate targeted patches:
    {
      "file": "viko.py",
      "patches": [
        {"before": "from viko.skills.web_search import...", 
         "after": "from viko.skills.web_search import...\nfrom viko.skills.crypto_price import crypto_price"}
      ]
    }
Untuk "prompt" → generate updated prompt.txt content penuh
```

Patch strategy: string-based replace (bukan AST manipulation) — lebih predictable untuk Gemini.

### backup.py

Tujuan: zero data loss sebelum setiap perubahan.

```
Struktur backup:
backups/
  2026-06-07_143022_viko.py
  2026-06-07_143022_viko__skills__crypto_price.py  (path separator → __)
  manifest.json

manifest.json entry:
{
  "id": "bk_001",
  "timestamp": "2026-06-07 14:30:22",
  "intent": "tambah skill crypto price",
  "files_changed": ["viko.py"],
  "files_created": ["viko/skills/crypto_price.py"],
  "restorable": true
}
```

Voice restore commands:
- *"Viko, kembalikan perubahan terakhir"* → restore manifest entry terbaru
- *"Viko, lihat history perubahan kamu"* → list manifest entries

### tester.py

Tujuan: validasi perubahan sebelum konfirmasi restart, dijalankan di subprocess terpisah.

```
Test sequence:
1. AST parse semua file yang diubah → syntax valid?
2. python -c "import <module>" → import clean?
3. Jika skill baru → panggil fungsi dengan mock args, cek tidak crash
4. Jika modifikasi core (viko.py/ui.py) → python -c "from viko.ui import VikoUI"

Hasil: PASS / FAIL + error message
On FAIL → rollback otomatis + announce error ke user
On PASS → announce: "Test berhasil. Restart VIKO sekarang?"
```

### restarter.py

Tujuan: restart VIKO secara graceful dari dalam proses sendiri.

```python
def restart():
    # 1. Simpan flag restart_pending di temp file
    # 2. QApplication.quit() di main thread
    # 3. os.execv(sys.executable, [sys.executable] + sys.argv)
    #    → replace proses dengan proses baru (no zombie)

# VIKO baru saat startup:
# - Cek restart_pending flag
# - Jika ada → announce via suara: "Saya sudah diperbarui dan siap"
# - Hapus flag
```

### engine.py

Tujuan: orchestrate seluruh pipeline, maintain state, handle error dan rollback.

```python
class SelfEngineerEngine:
    def run(self, intent: str, target_files: list[str] = None):
        # 1. ANALYZE
        context = analyzer.build_context(intent, target_files)
        
        # 2. PLAN
        plan = planner.generate(context)
        announce(plan["summary_for_voice"])  # via VIKO voice
        
        # 3. USER CONFIRM
        if not await_user_confirm("Lanjutkan?"):
            return "Dibatalkan."
        
        # 4. GENERATE
        changes = generator.generate(plan, context)
        
        # 5. BACKUP (sebelum apply)
        backup_id = backup.save(plan)
        
        # 6. APPLY
        apply_changes(changes)
        
        # 7. TEST
        result = tester.run(plan)
        if result.failed:
            backup.restore(backup_id)
            return f"Test gagal: {result.error}. Perubahan dibatalkan."
        
        # 8. USER CONFIRM RESTART
        announce("Test berhasil. Restart VIKO sekarang?")
        if await_user_confirm("Restart?"):
            restarter.restart()
        else:
            return "Perubahan tersimpan. Restart manual untuk mengaktifkan."
```

---

## Voice Tool Declaration

```python
# di viko.py TOOL_DECLARATIONS
{
    "name": "self_update",
    "description": (
        "Modifikasi kode VIKO sendiri: tambah skill baru, fix bug, ubah perilaku/prompt, "
        "modifikasi UI, atau restore backup perubahan sebelumnya."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "description": "Deskripsi lengkap perubahan yang diminta user"
            },
            "target_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Opsional: file spesifik yang relevan"
            },
            "action": {
                "type": "string",
                "enum": ["create_skill", "fix_bug", "modify_prompt", "modify_ui", "restore", "history"],
                "description": "Kategori aksi"
            }
        },
        "required": ["intent", "action"]
    }
}
```

---

## Voice Trigger Examples

| Ucapan User | Action | Files Target |
|---|---|---|
| "Tambahkan skill untuk cek harga Bitcoin" | create_skill | viko/skills/ + viko.py |
| "Perbaiki bug di browser tool, tadi ada error" | fix_bug | viko/skills/browser_tool.py |
| "Mulai sekarang jawab lebih singkat" | modify_prompt | viko/prompt.txt |
| "Ubah warna UI jadi lebih gelap" | modify_ui | viko/ui_theme.py |
| "Kembalikan perubahan terakhir" | restore | dari manifest |
| "Lihat history perubahan kamu" | history | manifest.json |

---

## Error Handling

| Kondisi | Respons |
|---|---|
| Analyzer gagal baca file | Announce error, tanya apakah user mau specify file manual |
| Planner gagal generate plan | Retry 1x dengan prompt yang lebih sederhana |
| Test FAIL | Rollback otomatis, announce error detail |
| Backup gagal (disk full) | Abort seluruh operasi, jangan apply apapun |
| Restart gagal | Perubahan tetap tersimpan, user restart manual |

---

## Constraints

- **Token budget analyzer**: maks ~20K tokens context per operasi
- **Patch size**: generator tidak rewrite seluruh file jika >200 baris; hanya patch bagian yang relevan
- **Backup retention**: simpan semua backup (tidak ada auto-delete); cleanup manual via perintah suara
- **Test timeout**: subprocess test max 30 detik sebelum dianggap FAIL
- **No git ops**: belum ada git commit otomatis; git dipakai manual setelah sistem terbukti stabil

---

## Out of Scope (untuk versi ini)

- Git-based versioning (diimplementasi setelah sistem stabil)
- Multi-step rollback (hanya 1 level restore untuk sekarang)
- Unit test generation (hanya smoke test)
- Remote deployment atau update dari server
