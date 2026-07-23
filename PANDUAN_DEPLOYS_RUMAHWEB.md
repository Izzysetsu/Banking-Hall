# 📦 Panduan Upload Siap Pakai ke Hosting Rumahweb (cPanel)

Dokumen ini berisi daftar **file bersih** yang siap di-zip dan di-upload ke cPanel Rumahweb kantor Anda.

---

## 📂 Daftar File & Folder yang HARUS Di-upload (Production Package)

Saat membuat file `.zip` untuk di-upload ke File Manager cPanel Rumahweb, **hanya sertakan file/folder berikut**:

```text
banking-hall-rumahsweb.zip
├── static/                   (CSS, JS, Icon, PWA Worker)
├── templates/                (Halaman HTML: index, admin, login)
├── .htaccess                 (Konfigurasi Limit Upload 500MB)
├── app.py                    (Main Backend Flask)
├── database.py               (SQLite Database Logic)
├── passenger_wsgi.py         (Gateway Python cPanel)
└── requirements.txt          (Daftar Modul Python: Flask & Werkzeug)
```

---

## 🚫 File/Folder yang JANGAN Di-upload:

- ❌ `__pycache__/` *(File temporary kompilasi lokal)*
- ❌ `.git/` *(History versi git)*
- ❌ `.vercel/` & `api/` *(Konfigurasi lama Vercel)*
- ❌ `.env` *(File kredensial Supabase lama)*
- ❌ `database.sqlite` *(Opsional: jika di-upload, akan menggunakan data lokal saat ini; jika tidak di-upload, aplikasi akan otomatis membuat file database baru yang bersih saat dinyalakan)*

---

## 🚀 4 Langkah Cepat Upload di cPanel Rumahweb:

1. **Buat Zip**: Pilih file/folder yang terdaftar di **Daftar File yang HARUS Di-upload** di atas, lalu Zip menjadi `banking-hall.zip`.
2. **Upload & Extract**: Masuk ke **cPanel -> File Manager**, upload `banking-hall.zip` ke folder domain kantor Anda, lalu klik **Extract**.
3. **Setup Python App di cPanel**:
   - Buka **Setup Python App** -> Klik **Create Application**.
   - **Python Version**: `3.10` / `3.11` / `3.12`.
   - **App Root**: Folder tempat extract tadi.
   - **App Startup File**: `passenger_wsgi.py`
   - **App Entry Point**: `application`
   - Klik **Create**.
4. **Install Modul**:
   - Di halaman Python App tadi, klik tombol **Run Pip Install** -> pilih file `requirements.txt`.

**Selesai!** Aplikasi Banking Hall Signage langsung aktif 100% menggunakan SQLite di server Rumahweb kantor.
