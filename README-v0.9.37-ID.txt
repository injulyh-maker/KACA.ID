KACA.ID v0.9.37 — OPTIMASI PREVIEW UNTUK RAM 8 GB

Target perangkat: AXIOO Hype 5, AMD Ryzen 5 3500U, Radeon Vega 8, RAM 8 GB dual-channel, dua kamera.

Perubahan:
- Preview webcam utama dibatasi maksimum 20 FPS.
- Preview kamera kedua dibatasi maksimum 15 FPS.
- JPEG preview dibatasi kualitas 80 dan ukuran maksimum 1280x720.
- JPEG preview dibuat secara lazy dari koneksi stream, maksimum satu encode per frame terbaru, lalu dibagikan ke seluruh koneksi MJPEG. Proses encode tidak berjalan di thread pembacaan kamera/Canon.
- Cache JPEG hanya menyimpan frame terbaru per kamera.
- Resolusi frame sumber untuk foto/capture tidak diturunkan; resize hanya terjadi pada jalur preview.
- Cache preview dibersihkan ketika kamera ditutup.
- Canon EDSDK, worker, native binding, DLL, dan jalur capture Canon tidak diubah.

Verifikasi:
Jalankan verify-kaca-id.bat pada Windows. Pengujian otomatis Python pada lingkungan pengembangan lulus. Kamera fisik dan performa pada AXIOO Hype 5 tetap harus diuji langsung di laptop pengguna.

Catatan:
FPS aktual bergantung pada sensor kamera, driver, suhu, serta beban Windows. Pengaturan ini merupakan batas maksimum stream preview, bukan jaminan FPS minimum.
