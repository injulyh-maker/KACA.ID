KACA.ID v0.9.63 — PATCH PERBAIKAN SLIDE HASIL

Masalah yang ditangani:
1. Countdown kembali ke Dashboard sekarang memakai deadline waktu absolut dan mulai berjalan segera setelah layar hasil dibuat. Countdown tidak bergantung pada keberhasilan handler WhatsApp/Email/Print.
2. QR Google Drive diminta melalui endpoint /qr.png setiap kali tautan folder tersedia. Backend dapat membuat QR secara lazy jika file QR belum dibuat saat status pertama kali diperiksa.
3. Live Photo menggunakan file WebM preview bila tersedia, dan memakai MP4 master sebagai fallback. Status loaded/error ditampilkan agar kegagalan codec tidak diam-diam terlihat seperti gambar macet.
4. CSS kiosk mempertahankan atribut hidden pada elemen video sampai video siap ditampilkan.
5. Endpoint render-status mengembalikan drive_qr_error untuk diagnosis.

CARA PASANG PATCH:
1. Tutup KACA.ID sepenuhnya.
2. Buat salinan cadangan folder src dan backend.
3. Ekstrak isi ZIP patch ke folder utama KACA-ID-v0.9.63-WINDOWS-BUILD-SOURCE.
4. Izinkan Replace untuk file yang sama.
5. Jalankan kembali run-kaca-id.bat.
6. Buat sesi BARU untuk menguji; jangan gunakan sesi yang sudah selesai sebelum patch.

FILE YANG DIGANTI:
- src/app.js
- src/style.css
- backend/camera_server.py

PENGUJIAN LINGKUNGAN PENGEMBANG:
- node --check src/app.js: PASS
- python -m py_compile backend/camera_server.py: PASS
- tests/result_slide_reliability_v0963_test.py: PASS
- tests/live_preview_dashboard_test.py: PASS
- tests/session_render_worker_v0963_test.py: PASS
- tests/filter_prefetch_v0944_test.py: PASS
- tests/live_photo_framed_preview_test.py: PASS
- tests/ui_layout_test.py: PASS
- tests/ui_frame_result_v0949_test.py: PASS
- tests/session_qr_test.py: PASS

Catatan: belum diuji langsung pada perangkat Windows/kamera/printer milik pengguna.
