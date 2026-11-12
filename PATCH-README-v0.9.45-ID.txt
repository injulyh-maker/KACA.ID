KACA.ID v0.9.45 — PATCH UI ALUR CUSTOMER

File patch:
- src/app.js
- src/style.css
- src/src/app.js
- src/src/style.css
- src.zip
- package.json
- README-v0.9.45-ID.txt
- tests_customer_flow_ui_v0945.py
- tests_fullscreen_v0944.py

Cara menerapkan:
1. Tutup aplikasi KACA.ID.
2. Ekstrak isi ZIP patch ke folder source proyek v0.9.44 dan pilih Replace/Timpa jika diminta.
3. Pastikan kedua file frontend di folder src/ dan src/src/ tertimpa.
4. Jalankan npm.cmd run dist:win untuk membangun installer Windows.

Perubahan hanya pada UI renderer, CSS, versi package, dokumentasi dan tes. Tidak ada file backend atau Canon EDSDK yang diubah.

Catatan penting:
Pilihan Voucher dan QRIS pada slide awal merupakan pilihan UI untuk meneruskan ke pemilihan frame. Integrasi pembayaran/gateway dan validasi voucher belum ditambahkan oleh patch UI ini.
