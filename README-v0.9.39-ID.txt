KACA.ID Photobooth v0.9.39

Pembaruan: QR Google Drive yang dapat diatur di dalam frame cetak.

Cara menggunakan:
1. Buka aplikasi KACA.ID sebagai Admin.
2. Masuk ke menu Pengaturan Frame.
3. Pilih frame yang akan digunakan.
4. Aktifkan "Sisipkan QR Google Drive ke hasil JPG untuk dicetak".
5. Seret kotak QR pada pratinjau ke posisi yang diinginkan.
6. Seret pegangan sudut QR untuk mengubah ukurannya.
7. Klik "Simpan Frame & Layout".
8. Hubungkan Google Drive sebelum sesi agar folder dan tautan sesi dapat disiapkan lebih awal.

QR menggunakan URL folder Drive sesi yang benar-benar dibuat oleh Google Drive.
Hasil JPG diperbarui jika URL baru tersedia setelah proses render awal. Jika Drive tidak terhubung,
QR tidak akan dibuat karena tidak ada tautan sesi yang valid.

ZIP dan Session_Info.json tetap disimpan lokal dan tidak diunggah ke Google Drive.

Untuk build Windows:
- Jalankan setup.bat
- Jalankan verify-kaca-id.bat
- Jalankan npm.cmd run dist:win

Pengujian otomatis: lihat PATCH-README-v0.9.39.txt.
Canon EDSDK files and DLLs are unchanged compared with v0.9.37 source.
