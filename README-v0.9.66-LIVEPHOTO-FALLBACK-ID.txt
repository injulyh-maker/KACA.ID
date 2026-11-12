KACA.ID v0.9.66 — PERBAIKAN LIVE PHOTO TIDAK TAMPIL DI SLIDE HASIL
==================================================================
Basis: KACA.ID v0.9.65 (QR Google Drive sudah berhasil tampil).

PENEMUAN
- Endpoint backend /qr.png sebelumnya dikonfirmasi HTTP 200 image/png, file valid.
- Endpoint /output_live.webm dikonfirmasi HTTP 200 video/webm; hal tersebut
  membuktikan unduhan file tetapi belum membuktikan dekoding/pemutaran di Electron.
- v0.9.65 menunggu event loadeddata sebelum memperlihatkan video. Jika dekoder
  menolak WebM atau event tidak pernah datang, JPG akan terus ditampilkan.
- Backend menyimpan MP4 memakai codec mp4v; file itu dapat berhasil dirender
  OpenCV meskipun tidak didukung oleh HTML5 video pada Electron tertentu.
- CSS v0.9.65 melarang interaksi pengguna dengan video (pointer-events:none).

PERBAIKAN v0.9.66
1. Video WebM diprioritaskan. Jika gagal/error/tidak siap dalam 9 detik,
   pemutar otomatis mencoba MP4. Semua peristiwa tampil dalam status Live Photo.
2. Bila kedua video tidak dapat diputar, aplikasi MEMBANGUN GIF ANIMASI dari
   frame video hasil dengan Python OpenCV + Pillow. Proses ini berlangsung di
   thread tersendiri (tidak memblokir backend). GIF adalah animasi yang bergerak,
   BUKAN pengulangan gambar JPG.
3. Endpoint baru: GET /api/session/<ID_SESI>/output_live.gif
   - HTTP 202 saat animasi sedang diproses.
   - HTTP 200 image/gif ketika animasi sudah siap.
   - HTTP 404 bila file video sumber benar-benar tidak tersedia.
   Frontend melakukan retry GIF otomatis tanpa mengganggu QR Google Drive.
4. Setelah media berhasil terbuka, JPG menjadi cadangan yang disembunyikan.
   Jika GIF/video gagal semua, JPG tetap ditampilkan plus tombol coba ulang.
5. Video kini dapat diklik untuk memutar ulang bila perlu.
6. GIF (khusus cadangan tampilan) disimpan dalam media/sessions/<ID>/output_live.gif
   serta Live_Photos/Live_Photo_Frame_Animasi.gif di arsip lokal jika tersedia.
   GIF beresolusi/frame-rate lebih rendah daripada video utama, demi kecepatan.
7. Proses kamera Canon, foto still, frame, QR, pembayaran, Drive upload, printer,
   WhatsApp, dan MP4/WebM master tidak diubah.

MEMASANG PATCH KE v0.9.65
1. Tutup aplikasi KACA.ID dan jendela terminal backend; pastikan tidak ada
   proses lama yang masih aktif pada port 8765.
2. Backup folder v0.9.65 dan data sesi/hasil yang sudah ada. JANGAN hapus
   %APPDATA%\kaca-id-photobooth\media\sessions atau folder Pictures/KACA STUDIO.
3. Ekstrak file ZIP patch ke folder UTAMA aplikasi (folder package.json).
   Ganti empat berkas source src/app.js, src/style.css,
   backend/camera_server.py dan package.json bila diminta.
4. Jalankan run-kaca-id.bat. Tidak perlu menjalankan setup.bat ulang selama
   dependensi yang sudah ada berfungsi.
5. Selesaikan satu sesi baru dan lihat slide hasil:
   QR tetap muncul; video dalam frame tampil otomatis lewat WebM/MP4, atau
   lewat mode ANIMASI jika dekoder browser menolak video.
6. Jika membuka EXE installer KACA.ID lama, mengubah folder source TIDAK akan
   mengubah EXE terinstal: bangun ulang installer atau jalankan source v0.9.66.

MEMASANG FULL SOURCE
- Ekstrak seluruh ZIP ke folder baru, lakukan setup sesuai README-INSTALL.txt,
  lalu jalankan run-kaca-id.bat dari folder tersebut.
- Sesi sebelumnya tidak dihapus atau dimigrasikan.

DIAGNOSTIK TAMBAHAN
- Log backend: [LIVE_GIF_FALLBACK_STARTED], [LIVE_GIF_FALLBACK_READY],
  [LIVE_GIF_FALLBACK_ERROR] bila generator mengalami masalah.
- Log frontend: [KACA_LIVE_RESULT], [KACA_RESULT_VIDEO_FALLBACK],
  [KACA_RESULT_LIVE_UNAVAILABLE].
- Perhatikan pesan status Live Photo tepat di bawah preview hasil.
- Mode GIF bekerja tanpa memerlukan internet dan tidak mengganti file MP4/WebM
  yang disimpan lokal/Google Drive.

VALIDASI SEBELUM RILIS
PASS: node --check src/app.js
PASS: python -m py_compile backend/camera_server.py
PASS: Chromium test (WebM sukses, GIF tidak diminta, QR sukses)
PASS: Chromium test (WebM dan MP4 gagal, GIF animasi sukses, QR sukses)
PASS: HTTP server Python 202 -> 200 image/gif dan GIF terdiri dari >1 frame
BELUM: pemutaran pada Windows/Canon/Electron perangkat booth pelanggan.

Catatan: Karena lingkungan booth sebenarnya tidak dapat diakses dari sini,
perbaikan ini belum boleh dianggap terbukti menyelesaikan masalah di PC booth
sampai diuji langsung. Jika masih gagal, sertakan teks status Live Photo dan
log dengan prefiks KACA_RESULT_VIDEO_FALLBACK / LIVE_GIF_FALLBACK_ERROR.
