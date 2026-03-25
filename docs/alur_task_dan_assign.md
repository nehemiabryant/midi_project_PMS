# Alur Fitur Task & Assignment PIC

## Daftar Isi
- [Database Tables](#database-tables)
- [Alur Assignment PIC](#alur-assignment-pic)
- [Alur Task CRUD](#alur-task-crud)
- [Alur My Work](#alur-my-work)
- [Struktur File](#struktur-file)

---

## Database Tables

### sr_ms_it (Master Role IT)
| it_role_id | it_role_detail |
|------------|---------------|
| 1 | IT GM |
| 2 | IT PMO |
| 3 | IT SM |
| 4 | IT SCM |
| 5 | IT DEV |
| 6 | IT QA |
| 7 | IT RO |

### sr_ms_ket (Master Status SR)
| smk_id | smk_ket | Keterangan |
|--------|---------|------------|
| 105 | BACKLOG SCRUM | SM bisa assign PIC |
| 106 | SD ON PROGRESS | Assignment locked, PIC mulai kerja |
| 108 | BACKLOG DEV | Territory DEV |
| 109 | DEV ON PROGRESS | Territory DEV |
| 110 | BACKLOG QA | Territory QA |
| 111 | QA ON PROGRESS | Territory QA |
| 114 | BACKLOG TO | Territory RO |
| 115 | TO ON PROGRESS | Territory RO |
| 116 | ROLLOUT | Territory RO |

### sr_assignments
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| assign_id | bigint (PK) | Auto-increment |
| sr_no | varchar (FK) | Referensi ke sr_request |
| assigned_user | varchar | NIK user yang di-assign |
| assigned_by | varchar | NIK user yang melakukan assign |
| it_role_id | bigint (FK) | Referensi ke sr_ms_it |
| assigned_at | timestamptz | Waktu assignment |

### sr_task
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| task_id | bigint (PK) | Auto-increment |
| assign_id | bigint (FK) | Referensi ke sr_assignments |
| task_detail | varchar | Deskripsi task |
| target_date | timestamptz | Target selesai (nullable) |
| actual_date | timestamptz | Tanggal aktual selesai (nullable) |

---

## Alur Assignment PIC

### Siapa yang bisa assign?
- Hanya **IT SM (it_role_id=3)** yang ter-assign pada SR tersebut.

### Kapan bisa assign?
- Hanya saat SR berstatus **105 (BACKLOG SCRUM)**.
- Setelah assignment dikonfirmasi, status otomatis berubah ke **106 (SD ON PROGRESS)** dan assignment **LOCKED** (tidak bisa diubah).

### Aturan Assignment
1. Wajib assign minimal **1 user per role** untuk 4 role berikut:
   - IT SCM (it_role_id=4)
   - IT DEV (it_role_id=5)
   - IT QA (it_role_id=6)
   - IT RO (it_role_id=7)
2. Boleh assign **multiple user** untuk 1 role (misal 2 DEV).
3. User yang bisa di-assign harus terdaftar di tabel `sr_user` dengan role **'User IT'** di `sr_ms_app_role`.
4. Semua insert assignment + update status dilakukan secara **ATOMIK** (1 transaksi, commit/rollback).

### Alur di Aplikasi
```
1. IT SM login
2. Buka halaman My Work (/myWork)
3. Melihat daftar SR yang di-assign ke dia
4. Klik "Details" pada SR → masuk halaman Detail SR (/myWork/detail/<sr_no>)
5. Di halaman Detail SR, ada section "Assign PIC"
   - Jika status 105: Tampil FORM untuk assign user per role
   - Jika status != 105: Tampil READ-ONLY (assignment locked)
6. SM pilih user untuk setiap role (min 1 per role)
   - Bisa tambah user per role dengan tombol "+ Tambah User"
7. Klik "Konfirmasi Assignment" → confirm dialog
8. Backend validasi:
   a. User = IT SM pada SR ini ✓
   b. SR status masih 105 ✓
   c. Min 1 user per 4 role ✓
   d. Semua NIK terdaftar sebagai User IT ✓
9. ATOMIC: INSERT ke sr_assignments + UPDATE sr_request.smk_id = 106
10. Redirect kembali → halaman sekarang tampil mode locked
```

### Routes
| Method | Route | Fungsi |
|--------|-------|--------|
| GET | `/myWork/detail/<sr_no>` | Halaman detail SR + section assignment |
| POST | `/myWork/detail/<sr_no>/assign` | Submit assignment PIC |

---

## Alur Task CRUD

### Siapa yang bisa CRUD task?
- Hanya user yang **ter-assign** pada SR tersebut via tabel `sr_assignments`.
- User hanya bisa melihat/CRUD task milik **role yang sama** (it_role_id sama).
  - Contoh: DEV 1 dan DEV 2 bisa saling lihat dan edit task karena sama-sama it_role_id=5.
  - QA tidak bisa lihat/edit task DEV, dan sebaliknya.

### Aturan Task
1. `task_detail` wajib diisi (tidak boleh kosong).
2. `target_date` dan `actual_date` opsional (nullable).
3. Task terhubung ke assignment via `assign_id` (FK ke sr_assignments).
4. Validasi akses:
   - CREATE: User harus ter-assign pada SR.
   - READ: User hanya lihat task dengan it_role_id yang sama.
   - UPDATE: User harus punya it_role_id sama dengan task owner.
   - DELETE: User harus punya it_role_id sama dengan task owner.

### Alur di Aplikasi
```
1. PIC (SCM/DEV/QA/RO) login
2. Buka My Work → klik SR → Detail SR
3. (Future: section Task di Detail SR)
4. Saat ini task diakses via API endpoint:

   GET  /task/list/<sr_no>        → List task sesuai role user
   POST /task/create/<sr_no>      → Buat task baru
   PUT  /task/<task_id>           → Update task
   DELETE /task/<task_id>         → Hapus task
```

### Request/Response Format

**CREATE Task:**
```json
POST /task/create/0001/SR/MUI-IT/SZ01/2026
Content-Type: application/json

{
    "task_detail": "Buat halaman login",
    "target_date": "2026-03-20T09:00:00+07:00",
    "actual_date": null
}

Response 201:
{
    "status": "T",
    "data": [[1]],
    "msg": "Task berhasil dibuat."
}
```

**GET Tasks:**
```json
GET /task/list/0001/SR/MUI-IT/SZ01/2026

Response 200:
{
    "status": "T",
    "data": [
        {
            "task_id": 1,
            "assign_id": 10,
            "task_detail": "Buat halaman login",
            "target_date": "2026-03-20T09:00:00",
            "actual_date": null,
            "assigned_user": "1234567890",
            "assigned_user_name": "Developer User"
        }
    ]
}
```

---

## Alur My Work

### Konsep
My Work adalah **pusat informasi** bagi setiap user yang login. Halaman ini menampilkan semua SR yang di-assign ke user tersebut, berdasarkan data di tabel `sr_assignments`.

### Data yang Ditampilkan
- **SR Number** dan judul/nama aplikasi
- **Status** SR (badge dengan warna sesuai status)
- **Tanggal dibuat**
- **Role user** pada SR tersebut (bisa multiple, misal SM + DEV)
- Tombol **"Details"** untuk masuk ke halaman Detail SR

### Halaman Detail SR (/myWork/detail/<sr_no>)
Terdiri dari beberapa section:

1. **Informasi SR** — Detail lengkap SR (nama, module, purpose, division, status, requester, dll)
2. **Role Anda** — Role user pada SR ini
3. **Tim SR** — Semua orang yang ter-assign pada SR (semua role)
4. **Assign PIC** (khusus IT SM) — Form assign atau read-only jika sudah locked

### Routes
| Method | Route | Fungsi |
|--------|-------|--------|
| GET | `/myWork` | List semua SR yang di-assign ke user |
| GET | `/myWork/detail/<sr_no>` | Detail SR + assignment + (future: task) |
| POST | `/myWork/detail/<sr_no>/assign` | Submit assignment PIC |

### Search
My Work mendukung pencarian berdasarkan SR number atau judul via query parameter `?q=keyword`.

---

## Struktur File

### Model (Database Query)
```
application/models/
├── my_work_model.py          # Query untuk My Work & Detail SR
│   ├── get_my_work_items_model()        # SR yang di-assign ke user
│   ├── get_sr_detail_full_model()       # Detail lengkap SR
│   ├── get_all_sr_assignments_model()   # Semua assignment pada SR
│   └── get_user_role_on_sr_model()      # Role user pada SR
│
├── assignment_model.py       # Query khusus assignment
│   ├── get_it_users_model()             # Daftar User IT
│   ├── get_assignable_picroles_model()  # Role yang bisa di-assign (4,5,6,7)
│   ├── get_sr_assignments_model()       # Assignment pada SR (filter role)
│   ├── get_sm_on_sr_model()             # Validasi SM pada SR
│   ├── get_sr_detail_with_status_model()# Detail SR + status
│   └── insert_assignments_and_update_status_model()  # ATOMIC insert + update
│
└── task_model.py             # Query khusus task
    ├── get_assignment_info_model()       # Cek user ter-assign pada SR
    ├── get_tasks_by_sr_and_role_model()  # Task berdasarkan SR + role
    ├── get_task_by_id_model()           # Single task untuk validasi
    ├── create_task_model()              # Insert task
    ├── update_task_model()              # Update task
    └── delete_task_model()              # Delete task
```

### Transaction (Business Logic)
```
application/transactions/
├── my_work_transaction.py    # Logic My Work & Detail SR
│   ├── get_my_work_trx()              # List My Work (group by SR, kumpulkan roles)
│   └── get_sr_detail_trx()            # Detail SR + validasi akses + data assignment
│
├── assignment_transaction.py # Logic Assignment
│   ├── get_assign_page_data_trx()     # Data halaman assignment (validasi SM)
│   └── submit_assignments_trx()       # Validasi rules + atomic insert
│
└── task_transaction.py       # Logic Task CRUD
    ├── get_tasks_trx()                # List task (validasi akses)
    ├── create_task_trx()              # Buat task (validasi akses)
    ├── update_task_trx()              # Update task (validasi role sama)
    └── delete_task_trx()              # Hapus task (validasi role sama)
```

### View (Routes/Controller)
```
application/views/
├── dashboard_view.py         # My Work + Detail SR + Submit Assignment
│   ├── GET  /myWork                          # List My Work
│   ├── GET  /myWork/detail/<sr_no>           # Detail SR
│   └── POST /myWork/detail/<sr_no>/assign    # Submit assignment
│
├── assignment_view.py        # Redirect ke detail SR (backward compat)
│   └── GET  /assignment/<sr_no>              # → redirect /myWork/detail/
│
└── task_view.py              # Task CRUD API
    ├── GET    /task/list/<sr_no>              # List tasks
    ├── POST   /task/create/<sr_no>           # Create task
    ├── PUT    /task/<task_id>                 # Update task
    └── DELETE /task/<task_id>                 # Delete task
```

### Template
```
application/templates/page/
├── my_work.html              # Tabel list SR di My Work
└── detail_sr.html            # Detail SR + section assignment
```
