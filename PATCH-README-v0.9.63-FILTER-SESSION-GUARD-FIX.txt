KACA.ID v0.9.63 — FILTER FINALIZATION GUARD FIX

Isi patch:
- src/app.js
- backend/camera_server.py

Perbaikan:
1. Tidak lagi diam-diam menghentikan finalisasi saat state UI busy atau session kosong.
2. Menunggu proses foto yang sedang berjalan sampai 15 detik.
3. Jika state sesi UI hilang, meminta backend memulihkan sesi aktif beserta daftar foto melalui GET /api/session/active.
4. Jika sesi tidak aktif, menampilkan alasan yang jelas di status Filter dan Console, bukan menganggap sesi sudah berhasil difinalisasi.
5. Hanya respons /api/session/finish yang benar-benar mengembalikan session ID yang dianggap sebagai finalisasi berhasil.
6. Mempertahankan perbaikan sebelumnya agar error tampilan setelah finalisasi tidak memicu finalisasi ulang.

CARA PASANG:
1. Tutup KACA.ID sepenuhnya.
2. Buat salinan cadangan folder src dan backend.
3. Ekstrak isi ZIP ke folder utama KACA-ID-v0.9.63-WINDOWS-BUILD-SOURCE, pilih Replace jika diminta.
4. Pastikan file masuk ke src/app.js dan backend/camera_server.py (bukan membuat folder bersarang).
5. Jalankan aplikasi dengan run-kaca-id.bat / perintah start yang biasa digunakan.
6. Uji satu sesi baru dari awal.

Catatan: pemeriksaan sintaks JavaScript dan Python lulus di lingkungan pengembangan. Belum diuji langsung pada perangkat Windows/kamera pengguna.
