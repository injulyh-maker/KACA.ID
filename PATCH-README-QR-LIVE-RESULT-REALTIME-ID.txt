KACA.ID v0.9.63 — PATCH QR + LIVE PHOTO PREVIEW SLIDE HASIL

Perbaikan:
- Countdown kembali ke Dashboard tidak lagi dimulai pada saat slide hasil baru dibuka.
- Countdown baru aktif setelah hasil render lokal tersedia, WebM Live Photo selesai dimuat pada browser (jika Live Photo diaktifkan), dan QR Google Drive telah tampil atau status Drive menunjukkan autentikasi/penyediaan gagal.
- Preview hasil lokal tidak harus menunggu proses upload Google Drive atau proses salin arsip lokal selesai.
- Endpoint render-status menyertakan status live_photo_enabled agar UI dapat menentukan apakah preview video perlu ditunggu.
- Saat QR image gagal dimuat, slide mencatat kondisi fallback dan tetap tidak menahan customer secara tidak terbatas.

Validasi dilakukan pada source menggunakan node --check, py_compile, dan script regression QR/live result slide.
