KACA.ID v0.9.49 - PERBAIKAN DETEKSI WEBCAM / DSLR

Perubahan:
1. Endpoint /health sekarang memeriksa OpenCV, bukan hanya status HTTP. Jika cv2 gagal diimpor, backend melaporkan HTTP 503 dan alasan yang jelas.
2. Endpoint /health menyertakan PID proses. Electron hanya menerima backend sehat jika PID cocok dengan proses Python yang baru dijalankan. Ini mencegah port 8765 dari backend lama dianggap sebagai backend yang baru.
3. Log startup backend mencatat executable Python, versi Python, dan versi OpenCV.
4. Pemindaian webcam mencoba DirectShow terlebih dahulu lalu Media Foundation (MSMF) setelah perangkat dilepas jika DirectShow tidak berhasil.
5. Jalur Canon EDSDK tetap terpisah dari OpenCV; deteksi Canon tidak diubah menjadi webcam OpenCV.

Cara memasang:
- Ekstrak full source v0.9.49 ke folder baru, atau terapkan patch ke source v0.9.47.
- Jalankan setup.bat sampai selesai agar .venv memasang semua dependensi.
- Jalankan run-kaca-id.bat.
- Buka Pengaturan > Perangkat Kamera > Deteksi Semua Kamera.
- Untuk Canon EOS, tekan Deteksi Canon EDSDK dan periksa status Canon EDSDK.

Catatan:
- Error Google Drive HTTP 401 invalid_client adalah masalah kredensial Google OAuth yang terpisah dan tidak menyebabkan webcam/DSLR gagal terdeteksi.
- SIGTERM pada saat aplikasi ditutup adalah sinyal penghentian backend yang dikirim Electron. Jika muncul saat aplikasi masih berjalan, kirim log lengkap di sekitar waktu tersebut.
- Build installer dan pengujian fisik webcam/Canon harus dilakukan pada PC Windows pengguna; pemeriksaan di sini hanya validasi source dan tes otomatis.
