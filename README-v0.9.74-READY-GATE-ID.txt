KACA.ID v0.9.74 — LOADING GATE & FRAME PRELOAD
===============================================
Basis: KACA.ID v0.9.73. Semua perubahan operasional pada alur layar pelanggan; backend kamera dan rendering tidak diubah.

PERBAIKAN 1: SESUDAH DASHBOARD
- Loading muncul tepat setelah customer memilih PHOTO dari Dashboard.
- Slide transaksi disembunyikan selama seluruh frame aktif diambil dan didekode.
- Apabila Voucher dan QRIS sama-sama nonaktif, slide transaksi tidak ditampilkan sama sekali.
- Bila transaksi aktif, loading selesai lebih dulu; halaman transaksi ditampilkan setelah frame siap. Setelah pembayaran, frame langsung terbuka tanpa mengulang loading yang tidak diperlukan.
- Kesalahan permintaan daftar frame atau kegagalan decode ditampilkan beserta tombol Coba Lagi.

PERBAIKAN 2: SEBELUM HASIL SESI
- Loading dimulai saat customer menekan LANJUT KE HASIL (sebelum finalisasi), bukan setelah slide hasil ditampilkan.
- Aplikasi menunggu render-status=ready dan pemeriksaan nyata JPG output.jpg dan QR qr.png (onload/decode).
- Untuk sesi Live Photo aktif, aplikasi mencoba output_live.webm dulu; bila gagal, output_live.mp4. Video harus benar-benar bergerak (currentTime maju) sebelum slide dibuka. Tidak menggunakan GIF.
- Foto, QR dan video yang sudah diuji dipindahkan ke tampilan hasil agar tidak perlu memulai pemuatan video dari nol.
- Timeout final tidak menyembunyikan loading otomatis. Bila proses tidak siap setelah tiga menit, aplikasi memberi alasan, Coba Lagi, atau Kembali ke Dashboard; file sesi tetap tersimpan.
- Countdown kembali ke Dashboard baru dimulai setelah slide hasil benar-benar ditampilkan.
- Upload Drive tetap asinkron; QR harus memuat tautan Drive yang sudah tersedia, tetapi tidak perlu menunggu semua file terunggah (yang mungkin memerlukan waktu lebih lama).

FILE PERBAIKAN
src/app.js, src/style.css, package.json, package-lock.json

PENGUJIAN PENGEMBANGAN
- Node.js --check: PASS
- Simulasi Chromium transaksi OFF / ON: PASS
- Simulasi Chromium alur penuh foto + Live Photo VP9/WebM + QR: PASS
- Pengujian perangkat booth dan Google Drive sungguhan: BELUM DILAKUKAN

CARA PASANG
1. Tutup KACA.ID dan backend sepenuhnya; backup folder lama.
2. Ekstrak PATCH, lalu salin ISI folder KACA-ID-v0.9.74-PATCH ke folder aplikasi v0.9.73 yang berisi package.json. Replace semua file yang diminta.
3. Jalankan run-kaca-id.bat.
4. Uji dari Dashboard hingga Pilih Frame, lalu satu sesi selesai sampai QR dan video hasil tampil.

CATATAN
Jangan menghapus data sesi di AppData atau Pictures\KACA STUDIO. Perubahan ini tidak memodifikasi file tersebut.
