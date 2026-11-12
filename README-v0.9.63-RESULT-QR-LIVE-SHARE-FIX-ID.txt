KACA.ID v0.9.63 — RESULT QR / LIVE PHOTO / SHARE FIX

Perubahan pada source:
1. QR sesi disajikan dari PNG lokal google_drive_qr.png. Jika file QR belum ada tetapi folder Drive sudah memiliki URL, backend membuat dan menyimpannya ulang secara lokal.
2. Status API membedakan QR yang benar-benar sudah tersimpan dari sekadar adanya URL Drive.
3. Layar hasil menampilkan status error QR/Drive yang lebih spesifik.
4. Live Photo dipasang ke elemen preview segera setelah aset live_output tersedia, tanpa menunggu status arsip lokal/Drive selesai.
5. Tombol simpan metode WhatsApp pada Pengaturan kini menampilkan pesan gagal jika penyimpanan setting ditolak.
6. Tombol Share pada daftar Output/Arsip mengikuti metode pengiriman yang dipilih: Click-to-Chat membuka WhatsApp dengan tautan Drive; Cloud API tetap menggunakan antrean WhatsApp.

PENTING:
- QR hanya dapat mengarah ke folder Google Drive setelah Google Drive berhasil terhubung dan folder sesi berhasil dibuat. Jika akun belum diotorisasi atau Google Drive gagal membuat folder, tidak ada URL yang sah untuk dimasukkan ke QR. Layar sekarang akan menampilkan penyebab/statusnya, bukan berpura-pura QR sudah siap.
- QR disimpan di komputer booth pada folder data sesi sebagai google_drive_qr.png dan tidak ditambahkan ke daftar upload Google Drive.
- File Live Photo master tetap MP4; WebM dipakai sebagai preview Chromium/Electron bila tersedia.
- Perubahan belum diuji pada kamera/printer/akun Google Drive Windows milik pengguna. Pengujian yang dijalankan di lingkungan pengembangan: Python compile, Node syntax check, dan tes terpilih (4 passed).

PENERAPAN PATCH:
1. Tutup KACA.ID.
2. Ekstrak ZIP patch.
3. Salin backend/camera_server.py ke folder aplikasi\backend\camera_server.py.
4. Salin src/app.js ke folder aplikasi\src\app.js.
5. Jalankan kembali run-kaca-id.bat.

Untuk salinan proyek lengkap, gunakan ZIP FULL SOURCE.
