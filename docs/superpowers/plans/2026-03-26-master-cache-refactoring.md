# Master Cache Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize semua hardcoded konstanta (role ID, status ID, territory map, NIK) yang tersebar di 6+ file ke dalam satu modul `master_cache.py` yang memuat data DB-derivable satu kali saat startup.

**Architecture:** Buat `application/utils/master_cache.py` sebagai satu-satunya sumber kebenaran untuk master data. Konstanta yang bisa diambil dari DB (role ID dari `sr_ms_it`, status ID dari `sr_ms_ket`, PIC territory dari `sr_ms_workflow_rules`) dimuat sekali saat `create_app()` dipanggil — tanpa query ulang per request. Konstanta yang tidak bisa di-DB (NIK, CSS class, territory oversight) tetap di file ini sebagai code constant terpusat, bukan tersebar di 6 file. Semua file yang terdampak menggunakan `master_cache` melalui **pemanggilan di dalam function body** (bukan module-level alias) agar tidak memicu DB call prematur saat import.

**Tech Stack:** Python, Flask, psycopg2 (via DatabasePG wrapper), PostgreSQL/Supabase

---

## File Structure

### File Baru
- `application/utils/master_cache.py` — cache terpusat, dimuat sekali saat startup

### File yang Dimodifikasi
| File | Perubahan |
|------|-----------|
| `application/__init__.py` | Tambah `master_cache.load_all()` di dalam `create_app()` |
| `application/models/assignment_model.py` | Hapus 7 konstanta hardcoded, fungsi gunakan `master_cache` dalam body |
| `application/models/my_work_model.py` | Hapus `IT_ROLE_TERRITORY`, SQL dinamis dari cache |
| `application/models/task_model.py` | Hapus `IT_ROLE_STATUS_MAP` (dead code) |
| `application/transactions/workflow_transaction.py` | Hapus 5 NIK, gunakan `master_cache` dalam function body |
| `application/transactions/my_work_transaction.py` | Hapus `STATUS_CLASS_MAP` + hardcoded role ID |
| `application/transactions/assignment_transaction.py` | Hapus re-deklarasi konstanta, gunakan `master_cache` dan `assignment_model.*` |

---

## Task 1: Buat `master_cache.py`

**Files:**
- Create: `application/utils/master_cache.py`

- [ ] **Step 1: Buat file dengan konstanta non-DB dan struktur internal**

```python
# application/utils/master_cache.py
"""
Central master data cache — dimuat sekali di app startup (create_app).
Eliminasi konstanta hardcoded tersebar di seluruh model/transaction files.

PENGGUNAAN:
  from ..utils import master_cache

  master_cache.get_role_id('IT SM')           # → 3
  master_cache.get_territory()                # → {4: [105, 106], ...}
  master_cache.get_status_class(105)          # → 'status-backlog'
  master_cache.IT_PM_NIK                      # → '0214083545'
"""
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

# ─── Konstanta Personnel (ubah di sini ketika ada pergantian jabatan) ─────────
# TODO: Pindahkan ke tabel sr_system_config di DB agar bisa diubah admin tanpa deploy
IT_PM_NIK = "0214083545"
IT_GM_NIK = "0201080005"
IT_SM_NIKS = {"0201080008", "0208010095", "0208080011"}  # DW, BS, OPS

# ─── Konstanta UI: status → CSS class (ubah ketika tema frontend berubah) ─────
# TODO: Pindahkan ke kolom 'status_class' di tabel sr_ms_ket agar fully DB-driven
STATUS_CLASS_MAP = {
    101: 'status-new',      102: 'status-review',   103: 'status-approved',
    104: 'status-rejected', 105: 'status-backlog',  106: 'status-progress',
    107: 'status-done',     108: 'status-backlog',  109: 'status-progress',
    110: 'status-backlog',  111: 'status-progress', 112: 'status-done',
    113: 'status-rejected', 114: 'status-backlog',  115: 'status-progress',
    116: 'status-rollout',  117: 'status-done',     118: 'status-hold',
    119: 'status-cancelled', 120: 'status-takeout',
}

# ─── Territory Oversight: role yang memonitor lebih dari fase kerjanya sendiri ─
# Nilai ini perlu disesuaikan jika alur workflow berubah secara fundamental.
# Role lain (PIC: 4,5,6,7) territory-nya diambil dari DB di _load_territory().
OVERSIGHT_TERRITORY = {
    1: [104],                     # IT GM → hanya fase IT GM Review
    2: list(range(103, 117)),     # IT PM → monitor dari Review SR (103) hingga Rollout (116)
    3: list(range(105, 117)),     # IT SM → monitor dari Backlog Scrum (105) hingga Rollout (116)
    8: [102],                     # Atasan/nik_up → hanya fase Review SR (102)
}

# ─── App role name untuk filtering user IT ────────────────────────────────────
IT_USER_ROLE_NAME = 'IT USER'

# ─── Internal cache store — diisi oleh load_all() ────────────────────────────
_DATA: dict = {
    'loaded': False,
    'it_roles': {},          # {it_role_id (int): it_role_detail (str)}
    'it_roles_inv': {},      # {it_role_detail (str): it_role_id (int)}
    'statuses': {},          # {smk_id (int): smk_ket (str)}
    'statuses_inv': {},      # {smk_ket (str): smk_id (int)}
    'territory': {},         # {it_role_id (int): [smk_id, ...]}
    'assignable_pic_ids': [], # [4, 5, 6, 7] — role PIC yang bisa di-assign SM
}
```

- [ ] **Step 2: Tambahkan `load_all()` dan loader privat**

Lanjutkan file yang sama:

```python
def load_all() -> None:
    """
    Muat semua master data dari DB. Panggil sekali di create_app().
    Setelah dipanggil, semua accessor berjalan dari memory — tanpa query DB per request.
    """
    _load_it_roles()
    _load_statuses()
    _load_territory()
    _DATA['loaded'] = True
    Log.info(
        f"master_cache loaded: "
        f"{len(_DATA['it_roles'])} roles, "
        f"{len(_DATA['statuses'])} statuses, "
        f"{len(_DATA['territory'])} territory entries, "
        f"assignable PIC IDs: {_DATA['assignable_pic_ids']}."
    )


def _ensure_loaded() -> None:
    """Guard untuk non-startup contexts (e.g., standalone scripts, testing).
    Di production, load_all() sudah dipanggil di create_app() sebelum request pertama."""
    if not _DATA['loaded']:
        Log.warning("master_cache: lazy-loading dipicu — pastikan load_all() dipanggil di create_app().")
        load_all()


def _load_it_roles() -> None:
    """Muat semua IT roles dari sr_ms_it."""
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            Log.error(f"master_cache: Gagal koneksi DB saat load IT roles: {conn.status.get('msg')}")
            return
        result = conn.selectHeader(
            "SELECT it_role_id, it_role_detail FROM sr_ms_it ORDER BY it_role_id"
        )
        if result.get('status'):
            for row in result.get('data', []):
                _DATA['it_roles'][row['it_role_id']] = row['it_role_detail']
                _DATA['it_roles_inv'][row['it_role_detail']] = row['it_role_id']
    except Exception as e:
        Log.error(f"master_cache: Exception di _load_it_roles: {e}")
    finally:
        if conn: conn.close()


def _load_statuses() -> None:
    """Muat semua status dari sr_ms_ket."""
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            Log.error(f"master_cache: Gagal koneksi DB saat load statuses: {conn.status.get('msg')}")
            return
        result = conn.selectHeader(
            "SELECT smk_id, smk_ket FROM sr_ms_ket ORDER BY smk_id"
        )
        if result.get('status'):
            for row in result.get('data', []):
                _DATA['statuses'][row['smk_id']] = row['smk_ket']
                _DATA['statuses_inv'][row['smk_ket']] = row['smk_id']
    except Exception as e:
        Log.error(f"master_cache: Exception di _load_statuses: {e}")
    finally:
        if conn: conn.close()


def _load_territory() -> None:
    """
    Derivasikan territory PIC roles dari sr_ms_workflow_rules.allowed_picrole.
    Territory oversight (GM=1, PM=2, SM=3, Atasan=8) diambil dari OVERSIGHT_TERRITORY.
    Jika DB memiliki data untuk role oversight, akan dilog sebagai warning (override terjadi).
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            Log.error(f"master_cache: Gagal koneksi DB saat load territory: {conn.status.get('msg')}")
            return
        result = conn.selectHeader(
            """
            SELECT allowed_picrole, current_smk_id
            FROM sr_ms_workflow_rules
            WHERE allowed_picrole IS NOT NULL
            ORDER BY allowed_picrole, current_smk_id
            """
        )
        territory: dict = {}
        if result.get('status'):
            for row in result.get('data', []):
                role_id = row['allowed_picrole']
                smk_id = row['current_smk_id']
                if role_id not in territory:
                    territory[role_id] = []
                if smk_id not in territory[role_id]:
                    territory[role_id].append(smk_id)

        # Periksa dan log jika DB punya data yang akan dioverride
        overlapping = [k for k in territory if k in OVERSIGHT_TERRITORY]
        if overlapping:
            Log.warning(
                f"master_cache: DB memiliki allowed_picrole untuk oversight roles {overlapping}. "
                f"Nilai dari OVERSIGHT_TERRITORY digunakan (override DB). "
                f"Update OVERSIGHT_TERRITORY di master_cache.py jika ini tidak diinginkan."
            )

        # Merge: OVERSIGHT_TERRITORY override DB untuk role oversight
        territory.update(OVERSIGHT_TERRITORY)
        _DATA['territory'] = territory

        # Assignable PIC roles = semua role dari DB rules yang bukan oversight
        _DATA['assignable_pic_ids'] = sorted([
            k for k in territory if k not in OVERSIGHT_TERRITORY
        ])
    except Exception as e:
        Log.error(f"master_cache: Exception di _load_territory: {e}")
    finally:
        if conn: conn.close()
```

- [ ] **Step 3: Tambahkan public accessor di akhir file**

```python
# ─── Public Accessors ─────────────────────────────────────────────────────────

def get_role_id(role_name: str) -> int | None:
    """Ambil it_role_id berdasarkan nama. Contoh: 'IT SM' → 3."""
    _ensure_loaded()
    return _DATA['it_roles_inv'].get(role_name)


def get_role_name(role_id: int) -> str:
    """Ambil nama role berdasarkan ID. Contoh: 3 → 'IT SM'."""
    _ensure_loaded()
    return _DATA['it_roles'].get(role_id, str(role_id))


def get_status_id(status_name: str) -> int | None:
    """Ambil smk_id berdasarkan nama. Contoh: 'Backlog Scrum' → 105."""
    _ensure_loaded()
    return _DATA['statuses_inv'].get(status_name)


def get_status_name(smk_id: int) -> str:
    """Ambil nama status berdasarkan ID. Contoh: 105 → 'Backlog Scrum'."""
    _ensure_loaded()
    return _DATA['statuses'].get(smk_id, str(smk_id))


def get_territory() -> dict:
    """Ambil full territory map: {it_role_id: [smk_id, ...]}."""
    _ensure_loaded()
    return _DATA['territory']


def get_assignable_pic_ids() -> list:
    """Ambil list role ID PIC yang bisa di-assign SM. Contoh: [4, 5, 6, 7]."""
    _ensure_loaded()
    return _DATA['assignable_pic_ids']


def get_status_class(smk_id: int) -> str:
    """Ambil CSS class untuk badge status. Contoh: 105 → 'status-backlog'."""
    return STATUS_CLASS_MAP.get(smk_id, 'status-default')
```

- [ ] **Step 4: Verifikasi import bersih (tanpa DB call)**

```bash
cd "/Users/cessac/Kuliah/Magang Alfamart/Project Magang/midi_project_PMS"
python -c "from application.utils import master_cache; print('Import OK, loaded:', master_cache._DATA['loaded'])"
```
Expected: `Import OK, loaded: False` — tidak ada DB call, tidak ada warning.

- [ ] **Step 5: Commit**

```bash
git add application/utils/master_cache.py
git commit -m "feat: add master_cache.py - centralized lazy-loaded master data cache"
```

---

## Task 2: Wire up Cache di `create_app()`

**Files:**
- Modify: `application/__init__.py`

- [ ] **Step 1: Tambahkan import dan panggilan `load_all()`**

Tambahkan di bagian atas (setelah import flask):
```python
from application.utils import master_cache
```

Tambahkan di dalam `create_app()`, tepat sebelum `return app` (bukan di dalam `app_context()`):
```python
    # Muat semua master data ke memory sekali saat startup
    master_cache.load_all()

    return app
```

> **Penting:** Jangan bungkus dengan `with app.app_context()`. `master_cache` tidak menggunakan Flask context variable sama sekali. Wrapper tersebut hanya menyesatkan pembaca kode.

- [ ] **Step 2: Jalankan dan verifikasi log startup**

```bash
python run.py
```
Expected di log awal startup: `master_cache loaded: X roles, Y statuses, Z territory entries, assignable PIC IDs: [...]`

- [ ] **Step 3: Commit**

```bash
git add application/__init__.py
git commit -m "feat: call master_cache.load_all() at app startup"
```

---

## Task 3: Update `assignment_model.py`

**Files:**
- Modify: `application/models/assignment_model.py`

**Aturan penting:** Jangan buat module-level aliases seperti `ASSIGNABLE_PICROLE_IDS = master_cache.get_assignable_pic_ids()`. Ini akan memicu DB call prematur saat import (sebelum `load_all()` dipanggil). Gunakan `master_cache.*` **di dalam function body** saja.

- [ ] **Step 1: Ganti blok konstanta di header**

Hapus baris 6–13 (seluruh blok `# Constants`). Tambahkan import:
```python
from ..utils import master_cache
```

Tetap pertahankan konstanta integer sebagai fallback yang **tidak memanggil DB**:
```python
# Fallback integer constants — nilai ini TIDAK boleh berubah tanpa sinkronisasi DB.
# Nilai aktual dimuat dari DB ke master_cache saat startup.
STATUS_BACKLOG_SCRUM = 105
STATUS_SD_ON_PROGRESS = 106
STATUS_IT_GM_REVIEW = 104
```

> Catatan: `ASSIGNABLE_PICROLE_IDS`, `IT_SM_ROLE_ID`, `IT_GM_ROLE_ID`, `IT_USER_ROLE_NAME` tidak lagi dideklarasikan di sini. File lain yang membutuhkannya menggunakan `master_cache` langsung.

- [ ] **Step 2: Update `get_it_users_model()`**

```python
def get_it_users_model() -> dict:
    sql = """
        SELECT su.nik, COALESCE(k.nama, '') AS nama
        FROM sr_user su
        JOIN sr_ms_app_role r ON su.approle_id = r.approle_id
        LEFT JOIN karyawan_all k ON su.nik = k.nik
        WHERE r.approle_name = %(role_name)s
        ORDER BY k.nama
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'role_name': master_cache.IT_USER_ROLE_NAME})
    except Exception as e:
        Log.error(f'DB Exception | get_it_users | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
```

- [ ] **Step 3: Update `get_assignable_picroles_model()`**

```python
def get_assignable_picroles_model() -> dict:
    """Ambil PIC roles yang bisa di-assign oleh SM (derivasi dari cache)."""
    pic_ids = tuple(master_cache.get_assignable_pic_ids() or [4, 5, 6, 7])
    sql = """
        SELECT it_role_id, it_role_detail
        FROM sr_ms_it
        WHERE it_role_id IN %(pic_ids)s
        ORDER BY it_role_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'pic_ids': pic_ids})
    except Exception as e:
        Log.error(f'DB Exception | get_assignable_picroles | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
```

- [ ] **Step 4: Update `get_sm_on_sr_model()` dan `get_gm_on_sr_model()`**

```python
def get_sm_on_sr_model(sr_no: str, nik: str) -> dict:
    sm_role_id = master_cache.get_role_id('IT SM') or 3
    sql = """
        SELECT sa.assign_id, sa.assigned_user, sa.it_role_id
        FROM sr_assignments sa
        WHERE sa.sr_no = %(sr_no)s
          AND sa.assigned_user = %(nik)s
          AND sa.it_role_id = %(sm_role)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'nik': nik, 'sm_role': sm_role_id})
    except Exception as e:
        Log.error(f'DB Exception | get_sm_on_sr | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
```

```python
def get_gm_on_sr_model(sr_no: str, nik: str) -> dict:
    gm_role_id = master_cache.get_role_id('IT GM') or 1
    sql = """
        SELECT sa.assign_id, sa.assigned_user, sa.it_role_id
        FROM sr_assignments sa
        WHERE sa.sr_no = %(sr_no)s
          AND sa.assigned_user = %(nik)s
          AND sa.it_role_id = %(gm_role)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'nik': nik, 'gm_role': gm_role_id})
    except Exception as e:
        Log.error(f'DB Exception | get_gm_on_sr | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
```

- [ ] **Step 5: Verifikasi — buka halaman My Work, tidak ada error**

- [ ] **Step 6: Commit**

```bash
git add application/models/assignment_model.py
git commit -m "refactor: assignment_model uses master_cache in function bodies, remove hardcoded constants"
```

---

## Task 4: Update `my_work_model.py` — Territory Dinamis + SQL Dinamis

**Files:**
- Modify: `application/models/my_work_model.py`

- [ ] **Step 1: Hapus `IT_ROLE_TERRITORY` dict, tambahkan import**

Hapus baris 6–15 (seluruh blok `IT_ROLE_TERRITORY`). Tambahkan:
```python
from ..utils import master_cache
```

- [ ] **Step 2: Refactor `get_my_work_items_model()` dengan SQL dinamis**

```python
def get_my_work_items_model(nik: str) -> dict:
    """
    Ambil semua SR yang di-assign ke user.
    Territory filter dibangun secara dinamis dari master_cache.get_territory()
    sehingga penambahan role/status baru tidak membutuhkan perubahan kode ini.
    """
    territory = master_cache.get_territory()
    if not territory:
        return {'status': False, 'data': [], 'msg': 'Territory kosong — pastikan master_cache.load_all() sudah dipanggil.'}

    # Build dynamic WHERE clause.
    # role_id adalah integer dari dict internal cache (bukan user input) — aman di-embed sebagai literal.
    conditions = []
    params: dict = {'nik': nik}
    for role_id, smk_ids in territory.items():
        if not smk_ids:
            continue
        key = f'smk_ids_{role_id}'
        conditions.append(f'(sa.it_role_id = {int(role_id)} AND r.smk_id IN %({key})s)')
        params[key] = tuple(smk_ids)

    territory_clause = ' OR '.join(conditions)
    sql = f"""
        SELECT r.sr_no, r.name, r.module, r.division,
               r.smk_id, COALESCE(s.smk_ket, '') AS smk_ket,
               r.created_at,
               sa.it_role_id, COALESCE(it.it_role_detail, '') AS it_role_detail
        FROM sr_assignments sa
        JOIN sr_request r ON sa.sr_no = r.sr_no
        LEFT JOIN sr_ms_ket s ON r.smk_id = s.smk_id
        LEFT JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.assigned_user = %(nik)s
          AND ({territory_clause})
        ORDER BY r.created_at DESC
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, params)
    except Exception as e:
        Log.error(f'DB Exception | get_my_work_items | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
```

- [ ] **Step 3: Verifikasi login tiap role — SR muncul sesuai territory**

Login sebagai IT SCM → status 107 tidak boleh muncul. Login sebagai IT PM → semua SR dari 103–116 muncul.

- [ ] **Step 4: Commit**

```bash
git add application/models/my_work_model.py
git commit -m "refactor: my_work_model derives territory from master_cache, dynamic SQL"
```

---

## Task 5: Update `task_model.py`

**Files:**
- Modify: `application/models/task_model.py`

- [ ] **Step 1: Hapus `IT_ROLE_STATUS_MAP` (dead code)**

`IT_ROLE_STATUS_MAP` tidak pernah digunakan di luar file ini (hanya definisi, tidak ada import di file lain). Hapus baris 6–12 beserta komentar TODO.

Tidak perlu tambahkan replacement apapun — model ini tidak punya kebutuhan territory saat ini.

- [ ] **Step 2: Commit**

```bash
git add application/models/task_model.py
git commit -m "refactor: remove unused IT_ROLE_STATUS_MAP from task_model"
```

---

## Task 6: Update `workflow_transaction.py`

**Files:**
- Modify: `application/transactions/workflow_transaction.py`

- [ ] **Step 1: Hapus 5 konstanta NIK dan `AUTO_ASSIGN_ON_PHASE` di header**

Hapus baris 10–21:
```python
# HAPUS SEMUA INI:
IT_PM_NIK = "0214083545"
IT_GM_NIK = "0201080005"
IT_SM_DW_NIK = "0201080008"
IT_SM_BS_NIK = "0208010095"
IT_SM_OPS_NIK = "0208080011"

AUTO_ASSIGN_ON_PHASE = {
    103: {'nik': IT_PM_NIK, 'it_role_id': 2},
    104: {'nik': IT_GM_NIK, 'it_role_id': 1},
}
```

Pastikan ada import di bagian atas:
```python
from ..utils import master_cache
```

- [ ] **Step 2: Update semua referensi NIK di `advance_sr_phase()`**

| Dari | Ke |
|------|----|
| `if action_by != IT_PM_NIK:` | `if action_by != master_cache.IT_PM_NIK:` |
| `if action_by != IT_GM_NIK:` | `if action_by != master_cache.IT_GM_NIK:` |
| `if action_by != IT_PM_NIK:` (di elif allowed_role==2) | `if action_by != master_cache.IT_PM_NIK:` |
| `if action_by not in [IT_SM_DW_NIK, IT_SM_BS_NIK, IT_SM_OPS_NIK]:` | `if action_by not in master_cache.IT_SM_NIKS:` |

- [ ] **Step 3: Ganti `AUTO_ASSIGN_ON_PHASE` dengan inline dict di dalam function**

Ganti blok step 7 di `advance_sr_phase()`:
```python
# Step 7. Auto-assign jika transisi ini memerlukan assignment otomatis
_auto_assign = {
    103: {'nik': master_cache.IT_PM_NIK, 'it_role_id': master_cache.get_role_id('IT PM') or 2},
    104: {'nik': master_cache.IT_GM_NIK, 'it_role_id': master_cache.get_role_id('IT GM') or 1},
}
if next_smk_id in _auto_assign:
    target = _auto_assign[next_smk_id]
    assign_result = assignment_model.insert_assignments_model(
        sr_no=sr_no,
        assignments=[{'nik': target['nik'], 'it_role_id': target['it_role_id']}],
        assigned_by=action_by,
        shared_conn=shared_conn
    )
    if not assign_result.get('status'):
        return {'status': False, 'msg': f"Failed to auto-assign: {assign_result.get('msg')}"}
```

- [ ] **Step 4: Update `authorize_sr_access()` — referensi `IT_PM_NIK`**

```python
# Ganti:
if user_nik == IT_PM_NIK:
# Dengan:
if user_nik == master_cache.IT_PM_NIK:
```

- [ ] **Step 5: Test approval flow end-to-end**

Test: Requester submit → Atasan approve → GM USER approve → IT PM advance → IT GM assign SM.

- [ ] **Step 6: Commit**

```bash
git add application/transactions/workflow_transaction.py
git commit -m "refactor: workflow_transaction uses master_cache for NIKs, remove AUTO_ASSIGN_ON_PHASE"
```

---

## Task 7: Update `my_work_transaction.py`

**Files:**
- Modify: `application/transactions/my_work_transaction.py`

- [ ] **Step 1: Hapus `STATUS_CLASS_MAP`, tambahkan import**

Hapus baris 8–30. Tambahkan:
```python
from ..utils import master_cache
```

- [ ] **Step 2: Update penggunaan `STATUS_CLASS_MAP`**

```python
# Dari:
'status_class': STATUS_CLASS_MAP.get(row.get('smk_id'), 'status-default'),
# Ke:
'status_class': master_cache.get_status_class(row.get('smk_id')),
```

- [ ] **Step 3: Update hardcoded role ID check di `get_sr_detail_trx()`**

```python
# Dari:
is_sm = 3 in user_role_ids  # IT SM = 3
is_gm = 1 in user_role_ids  # IT GM = 1
# Ke:
sm_role_id = master_cache.get_role_id('IT SM') or 3
gm_role_id = master_cache.get_role_id('IT GM') or 1
is_sm = sm_role_id in user_role_ids
is_gm = gm_role_id in user_role_ids
```

- [ ] **Step 4: Update referensi `IT_ROLE_TERRITORY` dan hardcoded PIC role list**

```python
# Dari:
territory_map = my_work_model.IT_ROLE_TERRITORY
pic_roles = [
    r for r in user_roles
    if r['it_role_id'] in [4, 5, 6, 7]
    and current_smk_id in territory_map.get(r['it_role_id'], [])
]

# Ke:
territory_map = master_cache.get_territory()
assignable_ids = master_cache.get_assignable_pic_ids() or [4, 5, 6, 7]
pic_roles = [
    r for r in user_roles
    if r['it_role_id'] in assignable_ids
    and current_smk_id in territory_map.get(r['it_role_id'], [])
]
```

```python
# Dari:
pic_assignments = [a for a in all_assignments_raw if a.get('it_role_id') in [4, 5, 6, 7]]
# Ke:
pic_assignments = [a for a in all_assignments_raw if a.get('it_role_id') in assignable_ids]
```

- [ ] **Step 5: Commit**

```bash
git add application/transactions/my_work_transaction.py
git commit -m "refactor: my_work_transaction uses master_cache for STATUS_CLASS_MAP and role IDs"
```

---

## Task 8: Update `assignment_transaction.py`

**Files:**
- Modify: `application/transactions/assignment_transaction.py`

- [ ] **Step 1: Hapus re-deklarasi konstanta duplikat di header (baris 9–13)**

```python
# HAPUS SEMUA INI:
ASSIGNABLE_PICROLE_IDS = assignment_model.ASSIGNABLE_PICROLE_IDS
STATUS_BACKLOG_SCRUM = assignment_model.STATUS_BACKLOG_SCRUM
STATUS_SD_ON_PROGRESS = assignment_model.STATUS_SD_ON_PROGRESS
STATUS_IT_GM_REVIEW = assignment_model.STATUS_IT_GM_REVIEW
```

Pastikan ada import:
```python
from ..utils import master_cache
```

- [ ] **Step 2: Update semua referensi di `submit_assignments_trx()`**

```python
# Dari:
if sr_detail.get('smk_id') != STATUS_BACKLOG_SCRUM:
# Ke: (gunakan assignment_model yang sudah punya integer fallback)
if sr_detail.get('smk_id') != assignment_model.STATUS_BACKLOG_SCRUM:
```

```python
# Dari:
role_names = {4: 'IT SCM', 5: 'IT DEV', 6: 'IT QA', 7: 'IT RO'}
assigned_roles = {a['it_role_id'] for a in assignments}
for it_role_id in ASSIGNABLE_PICROLE_IDS:
    if it_role_id not in assigned_roles:
        return {'status': False, 'data': [], 'msg': f'Minimal 1 user ... {role_names.get(it_role_id)}'}

# Ke:
assignable_ids = master_cache.get_assignable_pic_ids() or [4, 5, 6, 7]
assigned_roles = {a['it_role_id'] for a in assignments}
for it_role_id in assignable_ids:
    if it_role_id not in assigned_roles:
        role_name = master_cache.get_role_name(it_role_id)
        return {'status': False, 'data': [], 'msg': f'Minimal 1 user harus di-assign untuk role {role_name}.'}
```

```python
# Di advance_sr_phase call:
# Dari:
advance_result = workflow_transaction.advance_sr_phase(
    ..., current_smk_id=STATUS_BACKLOG_SCRUM, next_smk_id=STATUS_SD_ON_PROGRESS, ...
)
# Ke:
advance_result = workflow_transaction.advance_sr_phase(
    ..., current_smk_id=assignment_model.STATUS_BACKLOG_SCRUM,
    next_smk_id=assignment_model.STATUS_SD_ON_PROGRESS, ...
)
```

- [ ] **Step 3: Update NIK SM references di `get_gm_assign_page_data_trx()`**

```python
# Dari:
sm_niks = [
    workflow_transaction.IT_SM_DW_NIK,
    workflow_transaction.IT_SM_BS_NIK,
    workflow_transaction.IT_SM_OPS_NIK,
]
# Ke:
sm_niks = list(master_cache.IT_SM_NIKS)
```

- [ ] **Step 4: Update NIK SM validation di `submit_sm_assignment_trx()`**

```python
# Dari:
valid_sm_niks = {
    workflow_transaction.IT_SM_DW_NIK,
    workflow_transaction.IT_SM_BS_NIK,
    workflow_transaction.IT_SM_OPS_NIK,
}
# Ke:
valid_sm_niks = master_cache.IT_SM_NIKS
```

```python
# Dari:
if sr_detail.get('smk_id') != STATUS_IT_GM_REVIEW:
# Ke:
if sr_detail.get('smk_id') != assignment_model.STATUS_IT_GM_REVIEW:
```

- [ ] **Step 5: Commit**

```bash
git add application/transactions/assignment_transaction.py
git commit -m "refactor: assignment_transaction uses master_cache and assignment_model constants"
```

---

## Task 9: Verifikasi Akhir

- [ ] **Step 1: Cari sisa hardcode yang tertinggal**

```bash
grep -rn "IT_SM_ROLE_ID\|IT_GM_ROLE_ID\|ASSIGNABLE_PICROLE_IDS\|IT_ROLE_TERRITORY\|STATUS_CLASS_MAP\|IT_PM_NIK\|IT_GM_NIK\|IT_SM_DW_NIK\|IT_SM_BS_NIK\|IT_SM_OPS_NIK\|AUTO_ASSIGN_ON_PHASE" application/ --include="*.py"
```

Expected: Semua referensi yang tersisa hanya ada di `master_cache.py` saja.

- [ ] **Step 2: Smoke test semua role secara manual**

| Role | Aksi |
|------|------|
| Requester | Submit SR baru |
| Atasan (nik_up) | Approve 101→102 |
| GM USER | Approve 102→103, verifikasi IT PM otomatis ter-assign |
| IT PM | Approve 103→104, verifikasi IT GM otomatis ter-assign |
| IT GM | My Work → buka SR status 104 → assign IT SM |
| IT SM | My Work → buka SR status 105 → assign PIC team |
| IT SCM | My Work → status 107 tidak muncul, 105/106 muncul |

- [ ] **Step 3: Commit final (jika ada file yang belum di-commit)**

```bash
git add -u
git commit -m "refactor: complete master_cache integration - all constants centralized"
```

---

## Ringkasan: Apa yang Berubah

### DB-Driven (fleksibel tanpa perubahan kode)
| Data | Sumber DB | File Dulu |
|------|-----------|-----------|
| IT Role IDs & names | `sr_ms_it` | Hardcoded di 4+ file |
| Status IDs & names | `sr_ms_ket` | Hardcoded di 4+ file |
| PIC role territory (4–7) | `sr_ms_workflow_rules.allowed_picrole` | Dict hardcoded di 2 file |
| Assignable PIC role IDs | `sr_ms_workflow_rules` | `[4,5,6,7]` di 3 file |

### Masih Code Constant (terpusat di 1 file — ubah di `master_cache.py`)
| Data | Alasan | Langkah selanjutnya |
|------|--------|--------------------|
| NIKs (IT PM, GM, SM) | Perlu tabel `sr_system_config` baru | Buat tabel config |
| Oversight territory (GM/PM/SM) | Bergantung desain workflow | Bisa di-DB jika workflow berubah sering |
| STATUS_CLASS_MAP | Perlu kolom `status_class` di `sr_ms_ket` | Tambah kolom di DB |
