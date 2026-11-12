# KACA.ID v0.9.90 R1 — finalisasi source publikasi

**Status:** source siap diuji pada runner Windows. **Belum menjadi EXE/APK yang teruji.**
Versi aplikasi tetap **0.9.90** agar kompatibel dengan build workflow dan penamaan installer yang sudah disiapkan.

## Yang diperbaiki pada revisi R1

1. **Menu Lisensi KACA.ID:** pemeriksaan kelengkapan menu tidak lagi mencari tombol `#save` yang tidak ada; pemeriksaan ditujukan ke form lisensi nyata (server, booth, email, sandi, kode, tombol aktivasi dan cek offline).
2. **Loading hasil Live Photo:** tombol **Lewati Proses** kini terlihat saat loading, bukan baru setelah batas waktu habis. Pengguna langsung menuju hasil foto/QR, sementara file Live Photo dapat tetap disiapkan oleh backend.
3. **Status Cloud Control:** indikator `lisensi aktif` dipisahkan dari indikator `sinkronisasi Cloud tersambung`. Status sinkronisasi hanya online bila balasan sync terakhir masih baru (kurang dari 90 detik). Tombol Sinkronkan Sekarang memberi status sukses/gagal yang jelas.
4. **Lihat Paket & Harga:** URL resmi `https://kacastudio.id/paket` diizinkan oleh daftar URL eksternal Electron, tanpa membuka akses sembarang URL.
5. **Quality gate installer:** build lokal/CI menjalankan tes lisensi offline dan regresi menu lebih awal. Pemeriksaan berkas hasil installer menolak media pelanggan/contoh dan memeriksa komponen lisensi serta Cloud Agent.
6. **Sumber pembangun Python:** memakai pip host untuk mengambil wheel CPython 3.12 Windows x64 dan runtime embeddable Python 3.12.10; tidak mengharuskan NuGet atau mengganti Python global.

## Cara build Windows melalui GitHub Actions (disarankan)

1. Upload seluruh **isi** direktori `KACA-ID-PUBLISH/` ke **root** repository GitHub milik Anda. Sertakan folder tersembunyi `.github/workflows/`.
2. Pastikan tidak ada `runtime/`, `node_modules/`, `.env`, data pelanggan, kode lisensi, atau kunci privat masuk ke Git. `.gitignore` disiapkan untuk itu.
3. GitHub → Actions → **KACA.ID - Windows Installer (Python + VC++ included)** → **Run workflow**.
4. Bila job berhasil, unduh artifact `KACA-ID-Setup-0.9.90-x64`. Di dalamnya akan ada installer `.exe` dan `.sha256`.
5. Jalankan installer pada komputer uji Windows yang belum pernah memakai KACA.ID. Pastikan foto/frame/video lama tidak ada, lalu ikuti matriks uji di bawah. **Jangan langsung distribusikan ke pelanggan.**

## Cara build lokal Windows

Dari folder `KACA-ID-PUBLISH`, jalankan `build-windows-installer.bat` (Node.js + npm dan Python dengan pip hanya diperlukan di komputer pembangun; pengguna akhir tidak perlu memasang Python). Jika proses lulus, hasil ada di `dist/KACA-ID-Setup-0.9.90-x64.exe`. Jika gagal, lampirkan log dari pesan ERROR pertama. Jangan mendistribusikan installer yang gagal pada verifikasi.

## Matriks uji penerimaan wajib

| Uji | Kriteria lulus |
|---|---|
| Clean install | Dashboard tidak mengandung video/galeri atau frame dari booth sebelumnya. Branding KACA.ID tetap ada. |
| Tanpa aktivasi | PHOTO/VIDEO tidak dapat dimulai; halaman lisensi tetap dapat dibuka dan diisi tanpa error `#save`. |
| Aktivasi HTTPS | Input akun dan lisensi sah melakukan aktivasi ke `https://kacastudio.id` tanpa membuka booth ganda. |
| Lisensi offline | Setelah aktivasi, putuskan Wi-Fi; PHOTO/VIDEO masih dapat dimulai selama belum kedaluwarsa. |
| Kedaluwarsa | Gunakan lisensi **pengujian** yang benar-benar expired. Tidak boleh mulai sesi PHOTO/VIDEO baru. Jangan ubah tanggal PC pelanggan atau data lisensi produksi. |
| Asset pelanggan | Pelanggan memilih foto galeri, latar video, dan frame PNG sendiri; semua tetap tersedia saat aplikasi ditutup lalu dibuka. |
| Lewati loading | Tekan **Lewati Proses** saat Live Photo menunggu. Hasil foto/QR terbuka tanpa menunggu video. |
| Cloud sync | Saat internet aktif, booth tampil Online di Cloud Control. Matikan koneksi >90 detik: booth menjadi Offline, data lokal tidak hilang. |
| Remote | Hanya berjalan dengan izin lokal operator dan konfigurasi VPS remote aktif; default produksi tetap **nonaktif**. |
| Instalasi | EXE terbuka pada Windows x64 bersih tanpa menginstal Python global; periksa printer/webcam dan DSLR yang memang tersedia. |

## Catatan keamanan dan batasan

- **VPS produksi tidak disentuh.** Source `cloud_control/server.py` di paket ini adalah referensi. VPS Anda memiliki perubahan keamanan/MFA yang mungkin lebih baru: **jangan timpa file server VPS tanpa merge, backup, review, dan migrasi.**
- Lisensi Ed25519 ditandatangani dan diperiksa secara lokal; integritas sistem tetap bergantung pada perlindungan file/komputer pelanggan. Dalam perangkat offline sepenuhnya, aplikasi tidak memiliki sumber jam tepercaya yang tak dapat diubah, sehingga perlindungan anti-rollback adalah best effort, bukan jaminan anti-pembajakan absolut.
- Pada source saat ini, gate PHOTO/VIDEO utama ada di proses Electron/menu, belum merupakan lisensi yang tahan terhadap pengguna teknis yang memodifikasi source/bypass API lokal. Untuk penjualan massal, lakukan hardening entitlements pada backend lokal dan pinning kunci publik sebelum klaim DRM yang kuat.
- Distribusi Canon EDSDK/binding, font, dan semua aset pihak ketiga harus mematuhi hak redistribusi masing-masing. Pengujian fungsi kamera fisik, cetak, pembayaran, live photo, dan pengiriman WhatsApp perlu dilakukan pada lingkungan nyata.
- Proyek `android-tablet/` masih **beta**. Alur APK yang tersedia membuat **debug APK untuk pengujian**, bukan aplikasi Android publik setara Windows; fitur kamera Canon/DSLR, printer desktop, Live Photo dan alur penuh Windows tidak tersedia di beta.
- Jangan kirim kode lisensi/akun, file `.env`, kunci Ed25519 privat, atau hasil foto pelanggan ke repository publik.

## Pengujian source yang telah dilakukan di lingkungan kerja ini

- `node --check main.js`, `preload.js`, `src/app.js`, `cloud_control/agent.js`: lulus.
- `node tests/publish_license_offline_test.js`: lulus.
- `node tests/final_release_regression_test.js`: lulus.
- `python build/check-publish-assets.py`: lulus.
- `python build/test_packaging_configuration.py`: lulus.
- Tiga modul pengujian API Cloud dijalankan **pada proses Python terpisah**: lulus. Menjalankan tiga test suite dalam satu proses tidak valid untuk test fixture SQLite yang menginisialisasi modul server satu kali.
- Kompilasi NSIS EXE Windows, pemasangan pada komputer bersih, build APK Android, dan pengujian kamera/remote nyata **belum dilakukan dari lingkungan ini**.
