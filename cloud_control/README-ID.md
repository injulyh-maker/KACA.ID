# KACA.ID Cloud Control — Fondasi Multi Booth v0.9.86

Cloud Control adalah **server web** untuk mengelola banyak booth KACA.ID melalui akun pemilik dan Super Admin. Aplikasi booth tetap offline-first: kamera, frame, sesi, cetak, arsip lokal, dan Drive dikelola desktop, sementara sinkronisasi data dan perintah manajemen diantrikan secara online. **Bukan layanan cloud publik yang sudah dideploy.**

## Fitur yang sudah dibuat

| Modul | Mekanisme | Status |
|---|---|---|
| Akun pengguna | Registrasi email/password (Argon2) dan token sesi | API + web berjalan |
| Super Admin | Akun di-bootstrap via terminal, hanya role ini bisa menerbitkan lisensi | API + web berjalan |
| Lisensi per perangkat | Kode acak unik, satu lisensi untuk satu booth/device ID | API + desktop terhubung |
| Multi Booth | Satu akun dapat memiliki dan mengaktifkan beberapa lisensi | API + web berjalan |
| Offline | Lisensi Ed25519 ditandatangani server dan diverifikasi secara lokal | Teruji unit offline; tanpa cloud ketika internet mati |
| Analytics | Hitung sesi PHOTO/VIDEO dan pendapatan QRIS terverifikasi / estimasi terpisah | API + web berjalan |
| Hasil sesi | Metadata, link folder Google Drive; foto thumbnail hanya dengan persetujuan | API + web berjalan |
| Pengaturan jarak jauh | Harga, timer, mode PHOTO/VIDEO, lama Live Photo | Antrian perintah dan agen Electron |
| Kamera jarak jauh | Kontrol driver yang tersedia pada Kamera 1/2, baca balik hasil | API dan agen, perlu uji webcam/DSLR Windows |
| Voucher | Buat voucher kode dan kuota lewat antrean yang diterapkan saat booth online | API dan agen |
| Remote | Preview jendela aplikasi dan klik/ketik dengan izin operator 15 menit | Tahap awal; **bukan** remote seluruh Windows |
| Sinkronisasi | Data lokal tetap ada; antrean di userData dan retry setelah koneksi pulih | Agen desktop |

## Instalasi server web lokal

Dari folder KACA.ID (tempat `package.json` berada):

```powershell
py -m venv cloud-env
cloud-env\Scripts\python.exe -m pip install -r cloud_control\requirements.txt
$env:KACA_CLOUD_DATA_DIR = "D:\KACA-Cloud-Data"
cloud-env\Scripts\python.exe -m cloud_control.server init-admin --email admin@domainanda.id
cloud-env\Scripts\python.exe -m uvicorn cloud_control.server:app --host 127.0.0.1 --port 8086
```

Buka **http://127.0.0.1:8086** pada komputer server yang sama. Anda juga dapat mencoba pada Linux/macOS:

```bash
python3 -m venv .cloud-env
.cloud-env/bin/pip install -r cloud_control/requirements.txt
export KACA_CLOUD_DATA_DIR="$HOME/kaca-cloud-data"
.cloud-env/bin/python -m cloud_control.server init-admin --email admin@domainanda.id
.cloud-env/bin/python -m uvicorn cloud_control.server:app --host 127.0.0.1 --port 8086
```

> Jangan pakai URL HTTP untuk publik. Di internet pasang reverse proxy dengan **HTTPS**, firewall, backup, pengelolaan secret, email verification dan rate-limiting. SQLite cocok untuk uji awal; untuk banyak booth/produksi migrasikan ke PostgreSQL dan lakukan audit keamanan. Backup **database dan private key** secara bersamaan karena key penandatanganan lisensi tidak boleh berubah tanpa migrasi.

## Alur akun, lisensi, dan booth

1. Super Admin dibuat di server menggunakan `init-admin`, menggunakan password minimal 12 karakter yang dimasukkan secara tersembunyi di terminal.
2. Pengguna mendaftar akun melalui web Cloud Control.
3. Super Admin membuka **Super Admin → Buat Lisensi**, memasukkan email akun pengguna dan masa berlaku; kode lisensi lengkap hanya ditampilkan sekali.
4. Pengguna membuka desktop KACA.ID **Cloud Control → Aktivasi Akun / Lisensi**, memasukkan URL server HTTPS, email, password, kode lisensi, dan nama booth.
5. Agen menyimpan lisensi bertanda tangan Ed25519 dan kredensial booth di folder userData setempat. Booth tetap dapat menjalankan PHOTO/VIDEO tanpa cloud selama lisensi masih berlaku.
6. Untuk booth kedua, Super Admin menerbitkan **lisensi kedua** pada akun yang sama dan aktivasi pada perangkat kedua.
7. Tautan Drive, jumlah sesi, dan status booth muncul pada web setelah sinkronisasi.

### Migrasi pelanggan lama dan wajib akun

Untuk mencegah pemblokiran mendadak pada pelanggan KACA.ID versi lama, modul Cloud baru **tidak langsung mewajibkan** lisensi cloud pada instalasi existing; menu aktivasi sudah tersedia. Setelah booth berhasil diaktivasi, konfigurasi perangkat mewajibkan lisensi digital yang valid. Untuk pemasangan **baru** yang secara kebijakan harus login/lisensi sebelum memakai booth, set variabel lingkungan `KACA_REQUIRE_CLOUD_ACCOUNT=1` sebelum meluncurkan Electron. Saat belum ada lisensi atau sudah kedaluwarsa, jendela aktivasi modal akan menghalangi aplikasi.

Contoh PowerShell untuk instalasi baru:

```powershell
$env:KACA_REQUIRE_CLOUD_ACCOUNT = "1"
npm.cmd start
```

## Privasi dan offline

- File foto/video tetap dalam arsip lokal dan Google Drive yang sudah dikonfigurasi. Default Cloud hanya menyinkronkan metadata dan tautan Drive, **tidak mengunggah foto asli**.
- Pengguna bisa memilih `Izinkan unggah thumbnail foto` pada menu Cloud Control desktop. Tanpa persetujuan, tampilan web hasil sesi akan menampilkan link Drive saja.
- Antrian sinkronisasi disimpan pada `userData/kaca-cloud-outbox.json`. Kegagalan internet tidak menghapus antrian atau foto lokal.
- Jumlah **pengunjung** saat ini menggunakan jumlah sesi PHOTO/VIDEO; belum memakai deteksi orang unik.
- Pendapatan terverifikasi hanya dicatat untuk pembayaran yang diberi bukti status berhasil (contoh QRIS DOKU). Transaksi lain tidak otomatis dianggap berbayar.
- Remote dikirim lewat HTTPS, memerlukan login pemilik booth serta persetujuan lokal per 15 menit. Operator dapat mencabut izin dari menu Cloud Control. Tidak menyediakan akses shell atau file Windows dari browser.

## Penerapan patch desktop

Patch v0.9.86 dibuat berdasarkan FULL SOURCE **v0.9.85**. Tutup aplikasi dan backend Python, buat backup seluruh folder aplikasi serta data `AppData` dan `Pictures`, lalu salin isi folder PATCH ke akar aplikasi (sejajar `main.js` dan `package.json`). Jalankan `run-kaca-id.bat`. Pada installer Windows baru, `cloud_control/**/*` sudah ditambahkan ke `electron-builder build.files` agar agen dan layar aktivasi tidak hilang saat dipaketkan.

## Pengujian dan keterbatasan

Tes developer meliputi pembuatan akun pengguna, kontrol hak akses Super Admin, aktivasi dua booth dalam satu akun, binding lisensi Ed25519, audit lintas-akun, telemetry sesi, analytics, preview yang memerlukan izin remote, perintah yang tidak diizinkan, serta uji antarmuka web Chromium simulasi. Pengujian Windows/Electron sungguhan, kontrol DSLR, hosting internet, SLA, backup produksi, SMTP/MFA, dan pengiriman klik remote dari jarak jauh **belum** dilakukan. Cloud Control adalah fondasi implementasi, bukan remote desktop Windows penuh atau layanan produksi tersertifikasi.
