# KACA.ID Photobooth v0.9.26 — Dashboard Modes, Video Capture & Visual UI Designer

## Perubahan v0.9.26
- Pengaturan Umum kini memiliki sakelar **Tampilkan mode PHOTO** dan **Tampilkan mode VIDEO**. Mode yang dinonaktifkan tidak ditampilkan pada dashboard. Default kedua mode aktif agar konfigurasi lama tetap kompatibel.
- Perekaman video menggunakan frame dari kamera aktif. Sumber dapat berupa kamera utama atau Angle 2 MultiCam (webcam/OpenCV atau Canon EDSDK). Backend merekam frame secara konsisten pada 20 FPS, memeriksa jumlah frame sebelum mengembalikan hasil, dan menampilkan pesan kesalahan yang lebih spesifik.
- Endpoint perekaman video menerima pilihan angle dan menyediakan alias `/api/booth/video/start` untuk kompatibilitas.
- MultiCam memiliki tombol **Tampilkan Preview Kamera 1** dan **Tampilkan Preview Kamera 2** tepat di bawah masing-masing layar. Tombol menghubungkan perangkat terpilih lalu membuka stream preview secara terpisah.
- Advanced UI Designer diubah menjadi tab visual: **Dasbor**, **Preview Sesi**, **Pemilihan Frame**, **Filter**, dan **Slide Hasil**. Komponen pada kanvas dapat digeser dan diubah ukurannya dengan drag; warna, transparansi, dan skala diatur dengan picker/slider, tanpa memasukkan angka posisi/ukuran.
- Pengaturan tema visual disimpan di konfigurasi aplikasi dan diterapkan ke selector layar yang sesuai.
- Jalur Canon EDSDK utama tidak diubah.

## Cara memperbarui
1. Tutup KACA.ID sepenuhnya, termasuk proses backend yang masih berjalan.
2. Ekstrak patch ke folder source v0.9.25 dan izinkan overwrite, atau gunakan ZIP Full Project v0.9.26.
3. Pada Windows 10/11 x64, jalankan `build-windows-installer.bat`.
4. Setelah instalasi, jalankan `setup-python.bat` jika runtime Python/OpenCV belum disiapkan.

## Pengujian yang dilakukan
- `node --check main.js`, `node --check preload.js`, `node --check src/app.js`.
- `python -m py_compile` untuk backend kamera dan modul Canon.
- HTTP integration test `POST /api/video/start` dan `POST /api/video/stop` menggunakan frame sintetis; MP4 berhasil dibuat dan berisi frame.
- Uji writer video untuk sumber kamera utama dan kamera kedua dengan frame sintetis.
- Smoke test lama untuk komposisi frame, slot duplikat, dan arsip lokal.
- Integritas arsip ZIP diperiksa setelah dibuat.

## Belum dapat diverifikasi secara fisik
- Canon EOS 1300D USB/EDSDK sebagai Angle 2, webcam bersamaan, shutter, dan preview pada perangkat Windows.
- Dialog printer Windows dan hasil cetak.
- Pengalaman drag-and-drop UI Designer pada layar booth/touchscreen.
- Installer `.exe` tidak dibuat di lingkungan Linux. Jalankan batch build pada Windows.
