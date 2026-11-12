KACA.ID v0.9.87 — Webcam Controls + Loading Logo + PHOTO Layout
============================================================
Dibuat dari source lengkap v0.9.86 CLOUD CONTROL (bukan cabang lain).

PERUBAHAN
1. Logo pemuatan startup menggunakan logo KACA dari berkas kiriman pengguna.
   Aset asli tetap disertakan di src/assets/kaca-loading-brand-original.png.
   Aset tembus pandang untuk splash: src/assets/kaca-loading-brand.png.
2. Sesi PHOTO menempatkan preview lebar di atas, strip thumbnail foto di
   tengah, dan kontrol asli di bawahnya sesuai contoh referensi. Latar tetap
   biru tua KACA.ID. Tombol Switch Camera, Mirror, Shutter, Retake adalah node
   lama yang dipindah tanpa mengganti event handler. Tidak ada mic/streaming.
3. Kontrol profesional Kamera 1 dan Kamera 2 dipanggil dari status kamera aktif
   di backend, bukan hanya dari dropdown yang kadang kosong meskipun preview
   webcam berjalan. Panel kontrol muncul otomatis usai sambungan kamera.
4. Tombol Kembalikan Setelan Awal menyetel kembali pembacaan yang dicatat saat
   panel pertama diakses; tombol Pulihkan Warna Webcam mencoba saturasi nonnol
   yang sesuai skala driver secara eksplisit apabila kamera menjadi hitam-putih.
5. Reset Preview / Rotasi mengembalikan rotasi, flip, brightness aplikasi dan
   menyimpan setelan kamera tersebut. Tidak otomatis mengubah setelan kamera 2
   ketika pengguna me-reset kamera 1.

BATASAN
- Tidak semua webcam Windows/DSLR membolehkan ISO, Saturasi, Shutter, dll.
  OpenCV / driver dapat melaporkan nilai namun tetap menolak set; aplikasi
  menampilkan pesan kesalahan dan tidak mengklaim perubahan berhasil.
- Kembalikan Setelan Awal berarti snapshot driver saat panel pertama dibuka,
  BUKAN reset pabrik. Jika snapshot sudah hitam-putih, gunakan tombol Pulihkan
  Warna Webcam. Jika driver menolak, pulihkan melalui panel vendor/Windows.
- Hasil preview KACA pada uji Chromium menggunakan gambar referensi sintetis.
  Webcam fisik dan DSLR belum dapat diuji di mesin Windows pelanggan.
- PHOTO tetap memiliki slide Pilih Frame; VIDEO tetap menggunakan frame preset.
- QR, Google Drive, Event, Fonnte, retensi, Cloud Control tidak diubah.

PEMASANGAN PATCH
- Khusus untuk source KACA.ID v0.9.86 CLOUD CONTROL.
- Tutup KACA.ID dan backend Python. Backup source dan folder data Anda.
- Ekstrak paket PATCH; salin ISI folder KACA-ID-v0.9.87-PATCH ke folder
  aplikasi yang berisi package.json, replace saat diminta.
- Jalankan run-kaca-id.bat, buka Pengaturan Umum > Kamera & Video.
- Jika preview sudah aktif tetapi slider kosong, tekan Periksa Ulang Kamera.
- Lakukan satu sesi PHOTO untuk mengecek layout preview/thumbnail/kontrol.

PENGUJIAN PENGEMBANGAN
- Chromium: panel slider saat dropdown tidak terisi namun backend kamera aktif,
  saturasi 45->70->45, reset preview; lulus (backend tiruan).
- Chromium: PHOTO layout terukur di 1920x1080, 1440x900, 1188x901, 900x700;
  tombol tidak keluar layar, tidak ada mic/streaming; lulus (render mock).
- QR sesi, alur OAuth Drive mock, MultiCam, retensi, Live Photo, QR cetak;
  tes regresi lulus.
- Tidak ada klaim bahwa kontrol pada webcam fisik sudah teruji.
