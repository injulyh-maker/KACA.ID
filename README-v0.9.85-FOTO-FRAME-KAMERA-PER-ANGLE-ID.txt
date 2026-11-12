KACA.ID v0.9.85 — PILIH FRAME PHOTO + CAMERA PER-ANGLE
=============================================================
Dasar: KACA.ID v0.9.84 Full Source.

PERBAIKAN:
1. FOTO (PHOTO) kembali menampilkan slide Pilih Frame setelah transaksi
   atau setelah dashboard bila transaksi nonaktif. Semua frame aktif dan
   sesuai event di-preload sebelum slide dibuka. Frame yang dipilih
   pelanggan dipakai untuk komposisi, hasil cetak dan Live Photo.
2. VIDEO tetap TANPA slide Pilih Frame, memakai frame preset admin/Event.
3. Pengaturan Umum -> Kamera & Video -> Orientasi & Flip memiliki setelan
   kamera 1 dan kamera 2 terpisah (rotasi 0/90/180/270 dan dua jenis flip).
4. Preview kamera di Pengaturan Umum kini dibatasi dalam kotak 16:9; setelah
   90/270 derajat gambar tidak meluber ke tombol atau panel lain.
5. Kontrol profesional diletakkan di BAWAH layar preview masing-masing
   kamera berupa SLIDER, bukan input angka. Nilai awal dibaca dari driver,
   pergeseran dikirim per kontrol, dan nilai aktual dibaca balik. Jika
   driver menolak nilai atau hasilnya tidak cocok, UI menampilkan penolakan.
6. Slider Saturasi/Kontras/Brightness tidak lagi selalu 0-2. Backend
   memakai rentang perkiraan yang disesuaikan dengan nilai aktual OpenCV,
   termasuk webcam yang melaporkan saturation 0-100 atau 0-255.
7. Tombol Kembalikan Setelan Awal mengembalikan nilai yang tercatat
   ketika panel kamera diinisialisasi, bukan mengklaim factory reset.
8. Untuk kamera Canon EDSDK yang belum menyediakan kontrol melalui backend,
   slider palsu tidak ditampilkan; pengaturan DSLR dilakukan di kamera.
9. Per-kamera orientasi diterapkan pada frame foto, Live Photo, dan
   video mandiri yang direkam dari angle tersebut.

BATASAN PERANGKAT:
- OpenCV tidak mengekspos min/max native semua driver webcam. Sebagian
  rentang slider adalah perkiraan, didasarkan pada nilai yang dilaporkan
  driver, dan perubahan selalu diperiksa melalui readback. Respons sukses
  driver belum menjamin perubahan visual sama pada semua webcam.
- Pengujian kamera DSLR Canon, webcam asli Windows, dan hasil cetak fisik
  tidak dapat dilakukan tanpa perangkat pengguna.
- Jangan mengubah ISO/focus/exposure secara massal; atur per slider.
- Jika driver kehilangan warna meskipun nilai berhasil dikembalikan,
  gunakan tombol Kembalikan Setelan Awal, atau sambungkan ulang kamera.

INSTALASI:
Tutup aplikasi dan backend. Backup folder source serta data pelanggan.
Gunakan PATCH khusus untuk v0.9.84 dan salin isi folder patch ke root source
sejajar package.json, lalu jalankan run-kaca-id.bat.
Untuk aplikasi dengan cabang cloud monitoring berbeda, jangan replace file
secara langsung sebelum source disatukan.

PENGUJIAN OTOMATIS:
- Browser Chromium: foto nontransaksi ke Pilih Frame, pilih frame kedua,
  sesi menggunakan frame kedua: PASS.
- Browser Chromium: voucher valid ke Pilih Frame: PASS.
- Browser Chromium: VIDEO langsung ke Rekam, tanpa Pilih Frame: PASS.
- Browser Chromium: Kamera 1 & 2 memiliki orientasi terpisah: PASS.
- Browser Chromium: saturation 50->75->50 dan rotasi 90 tetap dalam panel: PASS.
- Python synthetic backend: range berbeda per driver, saturasi reset,
  penolakan perubahan, rotasi foto, dan dimensi video 90: PASS.
- Regresi: QR Google Drive, arsip Event, retensi, dan MultiCam: PASS.
