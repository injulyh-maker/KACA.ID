KACA.ID v0.9.63 — RESULT SLIDE ENTRY COUNTDOWN + QR/LIVE PREVIEW

Perbaikan sesuai revisi:
- Countdown slide sesi akhir mulai berjalan segera saat customer masuk ke slide hasil. Countdown tidak ditahan oleh proses render, persiapan QR, WebM Live Photo, archive lokal, ataupun upload Google Drive.
- Polling status hasil lokal tetap berjalan paralel; foto still/frame dimuat saat render lokal tersedia.
- QR Google Drive diambil dari endpoint QR lokal sesi setelah status/link folder diketahui. QR tampil berdasarkan ketersediaan link folder, tidak bergantung pada upload isi file Drive selesai.
- Video Live Photo/frame ditampilkan saat WebM browser preview siap, tanpa menunggu upload Drive.
- Penyimpanan/unggah berjalan background, bukan penghalang tampilan slide.

Validasi:
- node --check src/app.js: PASS
- tests/result_slide_reliability_v0963_test.py: PASS
- tests/result_originals_unfiltered_v0963_test.py: PASS

QR dan Live Photo perlu diuji lagi pada perangkat booth nyata dan Google Drive yang terhubung, karena lingkungan build tidak memiliki akses ke kamera dan akun Drive booth.
