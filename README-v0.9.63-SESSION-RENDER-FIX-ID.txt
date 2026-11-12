KACA.ID v0.9.63 — Perbaikan render hasil sesi

Perbaikan utama:
- Memperbaiki NameError pada worker render saat menerapkan filter. Worker sekarang membaca pengaturan kualitas JPEG dari snapshot sesi yang sedang diproses, bukan variabel lokal `session` yang tidak tersedia di thread worker.
- Ini mengatasi kegagalan render yang sebelumnya menyebabkan output.jpg 404 dan tombol Lanjut ke Hasil kembali menjadi Coba Lagi.
- Jalur kamera dan perekaman Live Photo tidak diubah.

Validasi:
- Jalankan skrip regresi satu per satu dari folder tests.
- Build Windows, kamera fisik, printer, dan otorisasi Google Drive perlu diuji di komputer operator.

Menjalankan aplikasi:
  npm.cmd install
  npm.cmd start
