# Panduan Testing — APD Monitoring System

**Capstone Project | Universitas Brawijaya 2026**  
Tim: Seronoknya Capstone

---

## Ringkasan

File `test_apd_system.py` berisi **51 test case** yang mencakup:

| Kategori | Jumlah Test | Modul yang Diuji |
|---|---|---|
| **Fungsional** | 26 | Workers, Captures, Detections, Violations, Root API |
| **Non-Fungsional: Performa** | 5 | Latensi tiap endpoint utama |
| **Non-Fungsional: Keandalan** | 7 | Toleransi error, input edge case |
| **Non-Fungsional: Keamanan** | 5 | Validasi file upload, type safety |
| **Non-Fungsional: Image Enhance** | 4 | Modul `image_enhance.py` langsung |
| **Non-Fungsional: Aksesibilitas** | 4 | Swagger UI, OpenAPI schema |

> **Catatan:** Testing dilakukan tanpa koneksi PostgreSQL — database di-mock sehingga bisa dijalankan di mesin manapun.

---

## Prasyarat

### 1. Python
Python 3.10 atau lebih baru. Cek versi:
```bash
python --version
```

### 2. Install dependencies

Masuk ke folder `backend/` terlebih dahulu:
```bash
cd apdMonitoringSystem/backend
```

Install semua package:
```bash
pip install -r requirements.txt
pip install pytest pytest-html httpx
```

Atau satu baris:
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-multipart python-dotenv pillow pydantic alembic pytest pytest-html httpx
```

> **Windows:** gunakan `pip` biasa.  
> **Linux/Mac:** jika error permission, tambahkan `--user` atau gunakan virtual environment.

### 3. Virtual Environment (opsional tapi direkomendasikan)

```bash
# Buat venv
python -m venv venv

# Aktifkan (Windows)
venv\Scripts\activate

# Aktifkan (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-html httpx
```

---

## Struktur File

```
backend/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   └── utils/
│       ├── image_enhance.py
│       └── notification.py
├── requirements.txt
├── test_apd_system.py      ← FILE TESTING INI
└── README_TESTING.md       ← FILE INI
```

---

## Cara Menjalankan Test

Semua perintah dijalankan dari folder `backend/`.

### Jalankan semua test (direkomendasikan)
```bash
pytest test_apd_system.py -v
```

### Jalankan hanya test fungsional
```bash
pytest test_apd_system.py -v -k "Fungsional"
```

### Jalankan hanya test non-fungsional
```bash
pytest test_apd_system.py -v -k "NonFungsional"
```

### Jalankan test berdasarkan kategori spesifik
```bash
# Hanya test performa
pytest test_apd_system.py -v -k "Performa"

# Hanya test keandalan
pytest test_apd_system.py -v -k "Keandalan"

# Hanya test image enhance
pytest test_apd_system.py -v -k "ImageEnhance"

# Hanya test workers
pytest test_apd_system.py -v -k "Workers"

# Hanya test detections
pytest test_apd_system.py -v -k "Detections"
```

### Jalankan satu test spesifik
```bash
pytest test_apd_system.py -v -k "test_verifikasi_detection_confirmed"
```

### Generate laporan HTML
```bash
pytest test_apd_system.py -v --html=laporan_testing.html --self-contained-html
```
Buka file `laporan_testing.html` di browser untuk melihat laporan lengkap.

### Tampilkan output print/log
```bash
pytest test_apd_system.py -v -s
```

### Ringkas (tanpa detail traceback)
```bash
pytest test_apd_system.py --tb=no -q
```

---

## Output yang Diharapkan

```
============================== test session starts ==============================
...
test_apd_system.py::TestFungsional_Root::test_root_returns_ok PASSED
test_apd_system.py::TestFungsional_Workers::test_tambah_pekerja_baru PASSED
...
test_apd_system.py::TestNonFungsional_Performa::test_latensi_root_dibawah_200ms PASSED
...
========================== 51 passed, 6 warnings in 1.0s =======================
```

---

## Bug yang Ditemukan Selama Testing

Dua test mendokumentasikan **bug nyata** yang ditemukan di kode produksi:

### Bug 1 — Telegram gagal → sistem crash (500)
**Test:** `TestNonFungsional_Keandalan::test_telegram_gagal_mengembalikan_500_bug_diketahui`

**Lokasi:** `app/routers/detections.py` baris ~115

**Masalah:** `send_telegram()` dipanggil tanpa `try/except`. Jika jaringan Telegram putus, seluruh request `/api/detections/report` gagal dengan 500.

**Perbaikan yang direkomendasikan:**
```python
# Sebelum (rentan crash):
send_telegram(f"<b>Anomali APD Terdeteksi</b>...")

# Sesudah (aman):
try:
    send_telegram(f"<b>Anomali APD Terdeteksi</b>...")
except Exception as e:
    print(f"[WARNING] Notifikasi Telegram gagal: {e}")
    # Data deteksi tetap disimpan, hanya notifikasi yang lewat
```

---

### Bug 2 — Upload file kosong → 500 bukan 400
**Test:** `TestNonFungsional_Keandalan::test_upload_file_kosong_bug_diketahui`

**Lokasi:** `app/routers/captures.py`

**Masalah:** File kosong (0 byte) lolos validasi tipe file, lalu Pillow gagal membuka file → `ResponseValidationError` karena `capture.id = None`.

**Perbaikan yang direkomendasikan:**
```python
# Tambahkan di awal fungsi upload_capture, setelah validasi content_type:
content = await file.read()
if len(content) == 0:
    raise HTTPException(status_code=400, detail="File tidak boleh kosong")

# Simpan content ke disk (jangan baca ulang dengan file.read()):
with open(save_path, "wb") as f:
    f.write(content)
```

---

## Deskripsi Test Case

### A. Pengujian Fungsional

#### F-01: Root API
| ID | Test | Deskripsi |
|---|---|---|
| F-01-01 | `test_root_returns_ok` | GET / mengembalikan status 'ok' dan info endpoint |

#### F-02: Workers
| ID | Test | Deskripsi |
|---|---|---|
| F-02-01 | `test_tambah_pekerja_baru` | POST berhasil menambah pekerja baru |
| F-02-02 | `test_tambah_pekerja_duplikat_employee_id` | Employee ID duplikat ditolak 400 |
| F-02-03 | `test_ambil_semua_pekerja` | GET mengembalikan daftar pekerja |
| F-02-04 | `test_ambil_pekerja_by_id_tidak_ada` | ID tidak ada → 404 |
| F-02-05 | `test_ambil_pekerja_by_id_valid` | ID valid → data pekerja benar |

#### F-03: Captures (Upload Foto CCTV)
| ID | Test | Deskripsi |
|---|---|---|
| F-03-01 | `test_upload_foto_jpeg_berhasil` | Upload JPEG valid → tersimpan + di-enhance |
| F-03-02 | `test_upload_foto_png_berhasil` | Upload PNG valid diterima |
| F-03-03 | `test_upload_foto_format_tidak_valid` | Upload MP4/dll ditolak 400 |
| F-03-04 | `test_upload_foto_enhance_gagal_tetap_tersimpan` | Enhance gagal → foto asli tetap ada |
| F-03-05 | `test_ambil_semua_captures` | GET mengembalikan daftar capture |
| F-03-06 | `test_ambil_capture_tidak_ada` | ID tidak ada → 404 |

#### F-04: Detections (Laporan AI & Verifikasi)
| ID | Test | Deskripsi |
|---|---|---|
| F-04-01 | `test_report_anomali_tanpa_helm_dan_rompi` | Laporan no-helmet+no-vest → unverified |
| F-04-02 | `test_report_anomali_tanpa_masker` | Laporan no-mask → tersimpan |
| F-04-03 | `test_notifikasi_telegram_dipanggil_saat_anomali` | Telegram WAJIB dipanggil |
| F-04-04 | `test_verifikasi_detection_confirmed` | Confirmed → violation baru otomatis terbuat |
| F-04-05 | `test_verifikasi_detection_false_alarm` | False alarm → tidak ada violation |
| F-04-06 | `test_verifikasi_detection_tidak_ditemukan` | ID salah → 404 |
| F-04-07 | `test_list_detections_tanpa_filter` | GET semua deteksi |
| F-04-08 | `test_list_detections_filter_unverified` | Filter status=unverified |

#### F-05: Violations (Dashboard & Statistik)
| ID | Test | Deskripsi |
|---|---|---|
| F-05-01 | `test_summary_struktur_respons_benar` | Summary punya semua 7 field |
| F-05-02 | `test_summary_nilai_numerik` | Semua nilai summary adalah integer ≥ 0 |
| F-05-03 | `test_ambil_semua_violations` | GET list pelanggaran |
| F-05-04 | `test_ambil_violation_tidak_ada` | ID tidak ada → 404 |
| F-05-05 | `test_update_status_violation` | PATCH status violation berhasil |
| F-05-06 | `test_verifikasi_violation_dengan_nama_pekerja` | Nama pekerja tersimpan saat verifikasi |

---

### B. Pengujian Non-Fungsional

#### NF-01: Performa
| ID | Test | Batas Waktu |
|---|---|---|
| NF-01-01 | `test_latensi_root_dibawah_200ms` | < 200 ms |
| NF-01-02 | `test_latensi_summary_dibawah_500ms` | < 500 ms |
| NF-01-03 | `test_latensi_upload_foto_dibawah_1000ms` | < 1000 ms |
| NF-01-04 | `test_latensi_list_pekerja_dibawah_300ms` | < 300 ms |
| NF-01-05 | `test_latensi_list_violations_dibawah_300ms` | < 300 ms |

#### NF-02: Keandalan
| ID | Test | Deskripsi |
|---|---|---|
| NF-02-01 | `test_endpoint_404_mengembalikan_json_bukan_html` | 404 = JSON bukan HTML |
| NF-02-02 | `test_upload_tanpa_file_mengembalikan_422` | Upload tanpa file → 422 |
| NF-02-03 | `test_verifikasi_tanpa_body_mengembalikan_422` | PATCH tanpa body → 422 |
| NF-02-04 | `test_verifikasi_status_tidak_valid_ditolak` | Status di luar enum ditolak |
| NF-02-05 | `test_enhance_gagal_tidak_mengganggu_report_deteksi` | Enhance gagal tidak crash endpoint |
| NF-02-06 | `test_telegram_gagal_mengembalikan_500_bug_diketahui` | **[BUG]** Telegram gagal → 500 |
| NF-02-07 | `test_upload_file_kosong_bug_diketahui` | **[BUG]** File kosong → 500 (harusnya 400) |

#### NF-03: Keamanan
| ID | Test | Deskripsi |
|---|---|---|
| NF-03-01 | `test_cors_header_tersedia` | CORS aktif untuk dashboard |
| NF-03-02 | `test_upload_script_php_ditolak` | File PHP ditolak 400 |
| NF-03-03 | `test_upload_file_teks_ditolak` | File TXT ditolak 400 |
| NF-03-04 | `test_worker_id_string_pada_url_ditolak` | ID berupa string → 422 |
| NF-03-05 | `test_confidence_score_di_luar_range` | Float bebas diterima API (validasi di AI) |

#### NF-04: Image Enhance
| ID | Test | Deskripsi |
|---|---|---|
| NF-04-01 | `test_enhance_menghasilkan_file_baru` | Output file berbeda dari input |
| NF-04-02 | `test_enhance_file_hasil_bisa_dibuka` | File hasil tidak corrupt |
| NF-04-03 | `test_enhance_tidak_mengubah_resolusi` | Resolusi gambar tetap sama |
| NF-04-04 | `test_enhance_gagal_jika_file_tidak_ada` | File tidak ada → exception |

#### NF-05: Aksesibilitas API
| ID | Test | Deskripsi |
|---|---|---|
| NF-05-01 | `test_swagger_ui_tersedia` | /docs bisa diakses |
| NF-05-02 | `test_openapi_schema_tersedia` | /openapi.json tersedia |
| NF-05-03 | `test_semua_endpoint_utama_terdaftar_di_schema` | 4 endpoint utama ada di schema |
| NF-05-04 | `test_content_type_json_pada_response_data` | Response pakai application/json |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'app'`**  
→ Pastikan menjalankan pytest dari folder `backend/`, bukan dari root proyek.

**`ImportError: cannot import name 'TestClient'`**  
→ Install httpx: `pip install httpx`

**`ERROR: No module named 'PIL'`**  
→ Install Pillow: `pip install pillow`

**Warning `PydanticDeprecatedSince20`**  
→ Warning ini aman, bukan error. Berasal dari kode produksi (schemas masih pakai class `Config` lama). Tidak mempengaruhi hasil test.

**Warning `MovedIn20Warning` (SQLAlchemy)**  
→ Warning ini aman. `declarative_base()` bisa dimigrasikan ke `sqlalchemy.orm.declarative_base()` di versi mendatang.
