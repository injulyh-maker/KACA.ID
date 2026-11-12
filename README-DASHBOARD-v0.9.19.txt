KACA.ID v0.9.19 — DASHBOARD REDESIGN
=====================================

Perubahan:
- Halaman awal menjadi dasbor KACA Studio dengan video animasi latar.
- Preview kamera otomatis mencoba membuka perangkat terakhir yang tersimpan.
  Canon menggunakan ID perangkat EDSDK tersimpan; webcam menggunakan indeks
  kamera yang tersimpan. Tombol MULAI membuka alur sesi foto lama.
- Ikon Home di kanan atas meminta PIN sebelum membuka pengaturan tampilan.
- Galeri thumbnail horizontal di bagian bawah dasbor. Lima thumbnail terlihat
  pada ukuran desktop umum dan strip bergerak otomatis; hover menghentikan gerak.
- Pengaturan tampilan memungkinkan penggantian judul, logo, video latar,
  warna tombol/panel/teks, tema terang/gelap, serta penambahan, penghapusan,
  dan pengurutan foto galeri.
- Foto, logo, dan video pilihan disalin ke folder data pengguna Electron agar
  tetap tersedia setelah aplikasi ditutup.

PIN awal:
- 1234
- Ganti PIN melalui Pengaturan Tampilan Dasbor setelah masuk pertama kali.

Cara menjalankan:
1. Ekstrak ZIP ke folder baru (jangan menimpa folder baseline v0.9.18).
2. Jalankan setup.bat jika lingkungan Python belum disiapkan.
3. Jalankan run-kaca-id.bat atau npm start.
4. Untuk mengelola tampilan, tekan ikon Home dan masukkan PIN 1234.

Catatan kompatibilitas:
- backend/canon_edsdk_live.py, backend/canon_edsdk_worker.py,
  backend/canon_edsdk_native.py, dan backend/camera_server.py dipertahankan
  identik dengan arsip v0.9.18 yang diunggah.
- Perubahan ini berfokus pada UI, pemilih aset, dan penyimpanan preferensi.
- Pemeriksaan sintaks JavaScript dan Python berhasil. Pengujian kamera fisik
  tetap perlu dilakukan pada komputer pengguna; perangkat Canon tidak dapat
  diuji dari lingkungan build ini.


OPTIMASI UI v0.9.20
- Posisi panel Live Preview pada dashboard diturunkan sedikit.
- Render penuh JPG/Live Photo/GIF tidak lagi dipicu setiap kali filter atau pilihan foto berubah. Render berat hanya dimulai ketika sesi benar-benar diselesaikan.
- Pratinjau filter memakai canvas 640px untuk mengurangi beban memori/GPU.
- URL foto pratinjau tidak lagi diberi cache-buster setiap render agar browser dapat menggunakan cache gambar.
- Canon EDSDK files are preserved unchanged from v0.9.19 baseline.
