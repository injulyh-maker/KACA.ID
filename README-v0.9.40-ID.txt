KACA.ID v0.9.40 - Perbaikan Preview Live Photo dan Kembali ke Dashboard

Perubahan:
1. Setiap rekaman Live Photo MP4 tetap disimpan sebagai master lokal.
2. Backend membuat pasangan WebM VP8/VP9 yang kompatibel dengan pemutar Chromium/Electron untuk preview di aplikasi.
3. Preview Live Photo pada slide review menggunakan URL WebM per foto, bukan output_live.webm yang belum dibuat.
4. Setelah render sesi selesai, preview hasil Live Photo dalam frame menggunakan file WebM hasil render.
5. Endpoint render-status mengirimkan nama file live_output_preview.
6. Detail sesi/arsip memakai WebM preview jika tersedia.
7. Tombol SELESAI dan hitung mundur hasil sesi mengembalikan aplikasi ke Dashboard utama, bukan ke slide preview kamera.
8. File Live Photo sementara per foto dibersihkan setelah video gabungan sesi selesai dibuat.

Catatan:
- MP4 asli tetap dipertahankan sebagai master hasil Live Photo.
- WebM merupakan file preview internal agar Chromium/Electron dapat memutarnya.
- Pembuatan WebM menambah proses encoding setelah perekaman; resolusi foto JPG tidak diubah.
- Canon EDSDK tidak diubah.
- Belum diuji pada kamera fisik pengguna; lakukan verifikasi pada AXIOO Hype 5 + EOS 1300D.

Build Windows:
  npm.cmd run dist:win
