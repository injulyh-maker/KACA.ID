KACA.ID v0.9.44 — FILTER PRE-RENDER & PREVIEW SIAP DI HASIL SESI

Pembaruan versi ini:
- Saat pelanggan masuk ke slide Pilih Filter, aplikasi otomatis mulai merender JPG final/frame dan Live Photo ber-frame di latar belakang.
- Perubahan filter atau pilihan foto di slide Filter menjadwalkan render ulang dengan jeda singkat agar klik yang berdekatan tidak membuat antrean render berlebihan.
- Tombol LANJUT KE HASIL menunggu render lokal selesai. Penantian ini hanya untuk menyiapkan hasil foto/Live Photo, bukan menunggu Google Drive.
- Slide Hasil Sesi menampilkan preview segera setelah render siap, tanpa menunggu penyalinan arsip lokal atau upload Google Drive.
- Jika Live Photo tersedia, preview JPG final dan video Live Photo ditampilkan bersamaan di slide hasil akhir (berdampingan pada layar lebar dan bertumpuk pada layar sempit).
- Klip sumber Live Photo dipertahankan selama pelanggan masih meninjau filter/pilihan foto sehingga render ulang tetap dapat dilakukan. Klip sumber dibersihkan setelah hasil final dikomit.
- Render awal tidak membuat salinan arsip lokal yang berpotensi berisi hasil sementara. Arsip lokal dibuat setelah sesi benar-benar diselesaikan.
- Retake menunggu render filter yang sedang berjalan selesai, lalu membatalkan cache render lama agar hasil foto pengganti tidak memakai preview yang sudah kedaluwarsa.
- Render yang sudah siap digunakan kembali ketika pelanggan menekan LANJUT KE HASIL; aplikasi tidak mengulang proses render yang sama.

Fitur yang tetap dipertahankan dari v0.9.43:
- Tombol Layar Penuh di Dashboard dan seluruh slide sesi.
- F11 untuk masuk/keluar layar penuh dan Esc untuk keluar.
- Ukuran jendela sebelumnya dipulihkan saat keluar dari layar penuh.
- Live Photo hasil sesi autoplay dan loop tanpa kontrol Play/Pause native.
- Slide Filter tetap hanya menampilkan preview foto statis; Live Photo tidak dimuat di slide tersebut.
- Penyimpanan lokal dan Google Drive tetap berjalan terpisah; preview tidak bergantung pada upload Drive.
- ZIP dan Session_Info.json tidak diunggah ke Google Drive.
- Jalur Canon EDSDK tidak diubah pada pembaruan ini.

Build installer Windows:
  npm.cmd run dist:win

Catatan pengujian:
- Pemeriksaan sintaks JavaScript dan Python berhasil.
- 12 regression test aplikasi berhasil, ditambah pemeriksaan fullscreen.
- 37 file Canon/EDSDK dibandingkan dengan source v0.9.43 dan tidak ada yang berubah.
- Installer Windows dan pengujian kamera fisik tidak dijalankan di lingkungan Linux ini. Lakukan pengujian akhir di PC Windows dan perangkat kamera yang digunakan.
