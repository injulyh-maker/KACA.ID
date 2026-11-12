# KACA.ID v0.9.90 — Paket Source Siap Build (Windows + Android beta)

**Status:** source telah dimodifikasi dan lolos pemeriksaan sintaks serta pengujian backend terisolasi. **Installer Windows `.exe` dan Android `.apk` belum dikompilasi** di lingkungan ini. Jalankan workflow GitHub Actions untuk menghasilkan berkas installer dan lakukan pengujian fisik sebelum publikasi pelanggan.

## Perubahan Windows

1. Installer tidak membawa `src/assets/dashboard-background.mp4`; dashboard pelanggan baru **kosong dari video/galeri contoh**. Video latar, galeri bergerak, logo tambahan, dan frame hanya berasal dari upload pengguna sendiri. Aset branding/icon KACA.ID tetap disertakan. Frame/sesi yang pernah disimpan di userData pelanggan lama **tidak dihapus** pada upgrade.
2. Menu **Lisensi KACA.ID** mempunyai form Server Cloud, email, password, kode lisensi, nama booth, serta tombol **Aktifkan Lisensi** dan pemeriksaan offline. Default server: `https://kacastudio.id` (bukan `127.0.0.1:8086`). Aplikasi juga memigrasikan konfigurasi server lama tersebut tanpa mencabut identitas booth.
3. Mode PHOTO dan VIDEO tidak dibuka dari aplikasi utama tanpa lisensi Ed25519 yang **sudah diaktivasi secara online**, sah untuk perangkat tersebut, dan **belum kedaluwarsa**. Sesudah aktivasi, pemeriksaan tanda tangan dan waktu kedaluwarsa dilakukan secara lokal tanpa internet. Perubahan jam yang mundur dibanding cap waktu terakhir disimpan akan ditolak. Saat lisensi kedaluwarsa, sesi **baru** terkunci; pengaturan dan aktivasi tetap bisa diakses. Implementasi ini adalah *functional application gate*, bukan jaminan tahan pembajakan terhadap modifikasi source/backend atau manipulasi waktu sebelum pemeriksaan awal.
4. Pada loading sebelum hasil akhir, tombol **Lewati Proses → Hasil Sesi** tidak menunggu preflight Live Photo. Foto hasil dan QR ditangani independen; Live Photo yang belum selesai dapat tampak sebagai placeholder sampai render selesai. Tombol ini **tidak** mengubah hasil foto asli.
5. Python 3.12 embeddable, dependensi kamera, dan VC++ disiapkan di **komputer builder**, dibundel dalam installer Windows, sehingga pelanggan tidak perlu memasang runtime Python terpisah. Perizinan redistribusi Canon EDSDK harus ditinjau sebelum menjual installer.

## Build installer Windows x64

**Paling mudah:** upload isi folder ini ke repository GitHub privat, buka tab **Actions**, pilih `KACA.ID - Windows Installer (Python + VC++ included)`, pilih **Run workflow**. Setelah job sukses, buka **Artifacts** dan unduh `KACA-ID-Setup-0.9.90-x64.exe`. GitHub runner menggunakan Windows 2022, Python builder 3.12, Node 22 dan menyiapkan Python portable serta VC++ di installer.

Alternatif pada PC **builder** Windows x64 yang memiliki Node 22 dan Python 3.12 x64:

```powershell
python build/check-publish-assets.py
node tests/publish_license_offline_test.js
./build/prepare-windows-runtime.ps1 -Force
npm.cmd ci --no-audit --no-fund
npm.cmd run dist:win
./build/verify-windows-installer.ps1
```

**Harus diuji pada PC baru:** install, unggah frame dan foto sendiri, aktivasi lisensi, cabut internet, mulai PHOTO/VIDEO, ubah jam secara wajar, tunggu lisensi uji berakhir, cek sesi terkunci, tekan Lewati Proses, cek rendering Live Photo terlambat, pencetakan, DSLR, QR Google Drive, pembaruan installer, dan ekspor arsip. Jangan publikasikan langsung hanya berdasarkan unit test Linux.

## Android/tablet — beta native, bukan port Windows

Folder `android-tablet/` berisi source Android Java/Gradle. Di GitHub Actions pilih `KACA.ID - Android Tablet APK (beta)` lalu Run workflow, unduh artifact `KACA-ID-Android-Tablet-0.9.90-beta-APK` dan instal `app-debug.apk` pada perangkat pengujian Android 13+. **APK debug hanya untuk pengujian pribadi**, bukan publikasi toko aplikasi. Distribusi produksi memerlukan release signing, pengujian kompatibilitas, kebijakan privasi, dan hardening.

Fitur beta: akun Cloud dan lisensi per tablet, validasi tanda tangan + kedaluwarsa offline, foto lewat kamera Android, upload PNG frame via file picker, simpan hasil ke Pictures/KACA-ID, antrean metadata sinkronisasi. **Belum tersedia** fitur Windows seperti DSLR Canon/EDS SDK, live photo, booth video, multiple frame-slot, printer, QRIS, Drive auto upload, WhatsApp Fonnte, remote screen, dan UI 6 slide. Tidak boleh memasarkan beta Android sebagai versi setara Windows.

## Cloud Control / email / paket harga

**PENTING:** Source `cloud_control/server.py` dalam ZIP berasal dari v0.9.89, sedangkan VPS yang sudah beroperasi diketahui memiliki versi berbeda dengan MFA dan modul `security_auth.py`. **JANGAN mengganti `server.py` VPS produksi langsung dengan file ini**: itu bisa menghilangkan keamanan/perubahan dari versi yang sedang live. Merge fitur baru ke source server produksi setelah membandingkan diff dan uji di staging. Backup **database SQLite dan file private key Ed25519 secara bersama-sama** sebelum migrasi.

Perubahan referensi API/web:

- Registrasi baru menunggu **email verification** sebelum login. Akun pelanggan lama tetap ditandai terverifikasi pada migrasi, sehingga data mereka tidak hilang.
- **Lupa sandi** mengirim tautan reset sekali pakai 20 menit; setelah reset sesi login lama dibatalkan, tetapi tabel booth, lisensi, sesi, foto, dan database tetap dipertahankan.
- Alur email hanya benar-benar terkirim jika SMTP dikonfigurasi dan diuji. Isi variabel di `cloud_control/email.env.example` secara aman **pada server**, jangan simpan password asli di ZIP/repository. SMTP harus mendukung TLS. Konfirmasi email, reset dan resend wajib diberi rate limiting WAF/reverse proxy tambahan sebelum publikasi massal.
- Halaman `https://kacastudio.id/paket` disiapkan untuk paket 30, 90, dan 365 hari. Karena harga belum ditentukan, awalnya **"Tanyakan harga"**. Harga rupiah dapat diisi Super Admin di panel **Harga Paket Lisensi di Website**. Tombol setiap paket membuka `https://wa.me/6281934386108` dengan pesan pilihan paket. **Belum ada checkout pembayaran otomatis atau gateway.**
- Koneksi lisensi memakai API di `https://kacastudio.id/api/...`, bukan `https://kacastudio.id/cloud/api/...`.
- Remote Control default **nonaktif** untuk referensi Cloud baru. Perlu audit dan persetujuan operator sebelum aktivasi (`KACA_CLOUD_REMOTE_ENABLED=1`), jangan aktifkan di produksi untuk testing akun pelanggan.

**Rute yang perlu digabungkan pada server live:** `POST /api/auth/resend-verification`, `POST /api/auth/verify-email`, `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`, `GET /api/public/plans`, `GET/POST /api/admin/plans`, dan halaman `/verifikasi-email`, `/reset-sandi`, `/paket`. Pertahankan autentikasi MFA, rate limits, audit, kebijakan SQL, dan semua data VPS saat ini.

Contoh konfigurasi Compose SMTP tersedia di `cloud_control/docker-compose.yml` untuk deploy baru. Jangan mengubah file `.env` di VPS tanpa backup dan pemeriksaan keamanan.

## Pemeriksaan yang sudah berjalan di source ini

```bash
python build/check-publish-assets.py
python build/test_packaging_configuration.py
node tests/publish_license_offline_test.js
python -m unittest cloud_control.tests.test_cloud -v
python -m unittest cloud_control.tests.test_cloud_web_v089 -v
python -m unittest cloud_control.tests.test_publish_auth -v
node --check src/app.js
node --check cloud_control/agent.js
node --check main.js
```

Semua pemeriksaan di atas dijalankan lokal pada source hasil modifikasi. **Belum ada pengujian akhir di Windows, Android, SMTP nyata, atau server VPS produksi** dalam percakapan ini.
