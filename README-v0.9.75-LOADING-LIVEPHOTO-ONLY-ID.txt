KACA.ID v0.9.75 — LOADING LIVE PHOTO SAJA SEBELUM HASIL AKHIR
========================================================
Basis: Full Source v0.9.74.

PERUBAHAN
- Loading dari slide Filter menuju Hasil Sesi hanya menunggu Live Photo yang benar-benar dapat diputar.
- Video WebM menjadi prioritas; jika tidak kompatibel/gagal, coba MP4.
- Keberhasilan dinilai saat video berhasil play dan currentTime terus maju, bukan hanya file ada.
- Tidak menunggu render_status=ready, preview JPG, QR Google Drive, local archive atau upload Drive.
- JPG hasil frame dan QR dimuat langsung di slide Hasil oleh mekanisme polling yang sebelumnya sudah berjalan.
- Jika Live Photo dinonaktifkan, gate video dilewati. Tombol LANJUT dan alur lain tidak berubah.
- Tidak menggunakan GIF animasi dalam slide hasil.
- Jika Live Photo benar-benar tidak dapat diputar dalam 3 menit, layar menawarkan Coba Lagi atau Kembali ke Dashboard; file sesi tidak dihapus.
- Loading awal setelah Dashboard dan preload semua frame aktif tetap mengikuti v0.9.74.
- Tidak mengubah kamera, renderer, Google Drive, printer, atau transaksi.

FILE DIUBAH
src/app.js, package.json, package-lock.json.

HASIL PENGUJIAN
- node --check src/app.js: LULUS.
- Chromium headless: gate dilewati ketika Live Photo nonaktif: LULUS.
- Chromium headless: WebM bergerak sebelum gate membuka hasil, walaupun JPG, QR, status render tidak tersedia: LULUS.
- Chromium headless: WebM tidak tersedia -> MP4 bergerak, tanpa menunggu JPG/QR/Drive: LULUS.
- Perangkat booth Windows dan akun Google Drive asli belum diuji.

PEMASANGAN PATCH
1. Tutup KACA.ID dan backend Python, lalu backup folder v0.9.74.
2. Ekstrak ZIP PATCH, salin isi folder KACA-ID-v0.9.75-PATCH ke folder aplikasi yang berisi package.json.
3. Replace file lama, jalankan run-kaca-id.bat.
4. Uji sesi dengan Live Photo aktif dan pastikan QR tetap muncul setelah slide Hasil Sesi terbuka.

Jangan menghapus folder foto, hasil sesi, frame, atau data pelanggan di AppData/Pictures.
