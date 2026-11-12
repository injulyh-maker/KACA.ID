KACA.ID v0.9.88 — PHOTO PREVIEW 16:9 + KONTROL DI DALAM + PEMULIHAN WEBCAM
============================================================================
Berdasarkan FULL SOURCE v0.9.87 Cloud Control. PHOTO/VIDEO, Live Photo, QR,
Event, Fonnte, lisensi dan Cloud Control tidak diubah selain perubahan berikut.

A. PHOTO / SLIDE PEMOTRETAN
- Tulisan/judul di atas live preview disembunyikan pada langkah 3 saja.
- Preview kamera berukuran responsif dengan rasio 16:9 (geometri 1920x1080).
- Frame camera stream tidak dipaksa 1920x1080, tidak ada pembesaran kualitas sensor.
- Tombol Switch Camera, Mirror, Shutter, dan Retake yang LAMA dipindahkan sebagai
  overlay pada bagian bawah di dalam layar preview, bukan diganti dengan tiruan.
- Tombol shutter tepat di tengah, switch/mirror kiri dan retake kanan.
- Strip foto/thumbnails tetap berada tepat di bawah preview.
- Pengaturan lain dan alur PHOTO/VIDEO tetap sama.

B. PEMULIHAN KAMERA WEBCAM
Akar masalah: pada versi sebelumnya, tombol Setelan Awal memakai angka
brightness/saturasi yang dibaca saat panel pertama dibuka. Jika webcam sudah
terlanjur gelap, snapshot itu ikut gelap, sehingga tombol reset justru
mengembalikannya ke kondisi bermasalah.

Kini ada:
- Pulihkan Kontrol Webcam: jika profil NORMAL pernah disimpan operator,
  terapkan nilai profil itu dan cek ulang nilai aktual driver.
- Jika belum ada profil NORMAL, gunakan perkiraan nilai netral brightness,
  contrast, saturation (50 pada skala 0..100 atau 128 pada skala 0..255),
  bukan menerapkan nilai awal yang dapat bernilai 0 / hitam.
- Pulihkan Warna Webcam: upayakan pemulihan saturasi saja (jangan reset ISO,
  gain atau exposure secara acak).
- Simpan Kondisi Normal: setelah kamera sudah bagus, simpan nilai driver
  yang terbaca menjadi profil tepercaya untuk reset berikutnya.
- Reset Preview / Rotasi: hanya mengatur ulang transformasi tampilan.
  Tidak mengubah driver fisik, dan tidak dianggap sebagai reset hardware.
- Jika driver tidak menerima nilai, tombol melaporkan penolakan secara jelas.

PEMBATASAN
OpenCV tidak melaporkan factory default UVC dari semua driver kamera. Tanpa
profil operator, reset memakai pendekatan nilai netral, BUKAN jaminan reset
pabrik 100 persen. Untuk reset pabrik driver, gunakan aplikasi pengaturan
kamera vendor/Windows. Kamera Canon EDSDK tidak menerima slider webcam palsu.

C. INSTALASI PATCH
1. Tutup KACA.ID dan backend Python; backup source v0.9.87 beserta AppData dan
   folder Pictures/KACA STUDIO terlebih dahulu.
2. Ekstrak PATCH dan salin ISI folder KACA-ID-v0.9.88-PATCH ke folder aplikasi
   yang sama dengan package.json; timpa file lama saat diminta.
3. Jalankan run-kaca-id.bat; aplikasi masih menggunakan Cloud Control sebelumnya.
4. Buka Pengaturan Umum > Kamera & Video, aktifkan Kamera 1, tekan Pulihkan
   Kontrol Webcam lalu periksa hasil live view.
5. Bila gambar sudah baik, tekan Simpan Kondisi Normal agar tombol pemulihan
   berikutnya memakai nilai yang Anda setujui. Uji PHOTO pada fullscreen.

D. PENGUJIAN OTOMATIS YANG TELAH DILAKUKAN
- Node.js syntax check src/app.js: LULUS
- Python compile backend: LULUS
- Chromium mock layout: 1920x1080, 1584x960, 1366x768, 1050x700, 700x840:
  preview 16:9, semua tombol dalam kotak preview: LULUS
- Chromium mock recovery: brightness=0/saturation=0 -> 50, profil operator
  tersimpan brightness 64 -> restore 64, reset rotasi: LULUS
- Chromium fake backend PHOTO frame->capture: tombol lama dan handler tetap ada: LULUS
- Backend fake webcam accepted/rejected controls: LULUS
- Regresi Google Drive QR, Event, retensi lokal/Drive, durasi Live Photo: LULUS
- Webcam fisik Windows/Canon belum diuji di lingkungan pengembangan.
