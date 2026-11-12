KACA.ID v0.9.63 — PATCH INFORMASI LOADING SLIDE

Perubahan:
- Menampilkan overlay “Tunggu kakak...😊” saat slide Frame, Filter, atau Hasil mulai dibuka.
- Overlay menampilkan pesan spesifik tahap slide.
- Indikator disembunyikan ketika preview frame/filter atau aset hasil (foto/Live Photo/QR) siap.
- Ada batas fallback 15 detik agar overlay tidak mengunci antarmuka jika aset tidak berhasil dimuat.
- Countdown slide akhir tetap berjalan seperti sebelumnya; loading overlay tidak mengubah countdown.
- QR dan Live Photo tetap diproses secara asynchronous, bukan menunggu upload Google Drive.

File yang diperbarui:
- src/app.js
- src/style.css

Validasi:
- node --check src/app.js berhasil.
- Perlu uji operasional pada perangkat booth, kamera, dan Google Drive sebenarnya.
