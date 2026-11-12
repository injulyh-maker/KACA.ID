KACA.ID v0.9.45 — PEMBARUAN UI ALUR CUSTOMER

Urutan slide customer:
1. Pilih Metode Transaksi (menggantikan layar Preview Kamera).
2. Pilih Frame: daftar frame vertikal di kiri dan preview frame besar di kanan.
3. Sesi Pemotretan: fungsi kamera, countdown, retake, MultiCam, dan galeri tetap dipertahankan; perubahan hanya pada layout.
4. Pilih Filter: preview frame di kiri, daftar foto di tengah, pilihan filter dan tombol lanjut di kanan.
5. Hasil Sesi: mempertahankan preview JPG/Live Photo, QR Google Drive, WhatsApp, email, cetak, dan hitung mundur kembali.

Catatan:
- Tombol Voucher dan QRIS pada slide pertama adalah pilihan metode pada UI untuk mengarahkan alur ke pemilihan frame. UI ini tidak memproses pembayaran atau memvalidasi voucher; integrasi pembayaran tetap mengikuti konfigurasi/backend yang tersedia.
- Kamera tetap disiapkan untuk tahap pemotretan, tetapi tidak lagi ditampilkan sebagai slide awal.
- Tidak ada perubahan pada backend maupun Canon EDSDK.
- ZIP dan Session_Info.json tidak diunggah ke Google Drive.

Build installer Windows:
  npm.cmd run dist:win
