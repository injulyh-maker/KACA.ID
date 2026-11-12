KACA.ID v0.9.69 — Preview Hasil & Filter OpenCV

Dasar: KACA.ID v0.9.68 (termasuk perbaikan kamera, QR, Live Photo, preload frame).

1. Layar hasil sesi:
   - Preview hasil foto (kiri) dan Live Photo (kanan) berdampingan dengan ukuran sama.
   - Live Photo autoplay, muted, loop, tanpa kontrol play/pause.
   - Tidak menampilkan pesan rendering/progres, label animasi, atau tombol pemutaran.
   - Saat video belum siap, panel kanan sementara memakai JPG hasil frame (bukan pesan loading).
   - QR, WhatsApp, email, tombol cetak, selesai, dan perhitungan waktu tetap ada.

2. Filter tambahan:
   - Sketsa Pensil (`pencil`): grayscale, invert, GaussianBlur 21×21, cv2.divide.
   - Kartun / Ilustrasi (`cartoon`): bilateralFilter(9,300,300), medianBlur 7, adaptiveThreshold block 9 C=2, bitwise_and.
   - Tersedia pada slide "Pilih Filter" dan pengaturan "Filter Foto".
   - Preview pada slide menggunakan OpenCV melalui endpoint lokal terbatas.
   - Filter dipakai saat render foto hasil dan Live Photo di backend. Foto original tidak diubah.

Pemasangan patch:
- Tutup KACA.ID dan backend Python.
- Backup folder aplikasi dan jangan hapus media/data sesi.
- Ekstrak PATCH, salin seluruh ISI folder PATCH ke folder utama yang berisi package.json, pilih Replace.
- Jalankan run-kaca-id.bat lalu lakukan sesi uji.

Pengujian dilakukan di lingkungan pengembangan: sintaks JS/Python, HTTP preview filter, status endpoint kamera, layout Chromium 1600×920 dan atribut autoplay. Belum diuji langsung dengan kamera fisik/installer Windows pelanggan.

Catatan: contoh pengguna memiliki typo `cap.read(06.2)`; kode ini menggunakan pemrosesan frame yang sudah dikelola aplikasi, bukan membuka webcam kedua.
