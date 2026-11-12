KACA.ID v0.9.82 — SHARE WHATSAPP, PIN & MENU RECOVERY
======================================================
Source dasar: KACA.ID v0.9.81 Full Source.

1. Tombol Share WhatsApp di Output & Cetak serta Arsip Sesi:
   - window.prompt() dihapus (tidak didukung Electron yang dipakai).
   - Muncul formulir nomor WhatsApp di dalam aplikasi, dengan persetujuan pelanggan.
   - Mode Gateway Fonnte menggunakan POST /api/whatsapp/fonnte/send, bukan /api/whatsapp/send.
   - Jika konfigurasi mode click_to_chat, baru WhatsApp akan dibuka (perilaku lama).
   - Jika Cloud API dipilih, tetap pakai integrasi Cloud API.
   - Token Fonnte yang sudah tersimpan di AppData tidak dihapus/ditimpa.
   - Setelah menyimpan token Fonnte, metode kirim diaktifkan otomatis sebagai Gateway Fonnte.
   - Untuk token lama yang sudah tersimpan namun metode belum berubah, buka Pengaturan Umum
     dan klik "Aktifkan Pengiriman Fonnte".
   - Cek token/perangkat/kuota melalui "Periksa Koneksi & Kuota Fonnte".
   - Respons diterima Fonnte berarti queued/accepted, BUKAN pesan sudah terkirim ke WhatsApp pelanggan.

2. File/Edit/View bawaan Windows/Electron:
   - Menu aplikasi native dihapus (Menu.setApplicationMenu(null), autoHideMenuBar).
   - Tombol Layar Penuh tetap dapat digunakan.

3. PIN Pengaturan (Admin/Operator):
   - Dibuat keypad angka inline tersendiri (bukan browser prompt atau keyboard layar eksternal).
   - Tombol Perbaiki Input (bersihkan/fokus kembali), Batal, dan tombol Masuk.
   - Tombol fullscreen tidak lagi menutupi tombol Admin di Dashboard.
   - Pilihan/perubahan PIN tetap menggunakan nilai adminPin tersimpan, tidak direset.

4. Pemulihan Menu:
   - Tombol Pulihkan Menu dapat menutup modal yang macet, lalu membuka kembali menu aktif.
   - Menu dengan loading >12 detik mendapat tombol Coba Muat Ulang.
   - Pintasan Ctrl+Alt+R memuat ulang hanya tampilan Electron, tidak menutup aplikasi.
     Catatan: bila sedang merekam, selesaikan sesi lebih dulu agar state UI tidak hilang.
   - Konfirmasi penghapusan/aksi admin menggunakan dialog dalam aplikasi, bukan confirm() native.
   - Mode PHOTO/VIDEO pelanggan tidak diubah oleh fungsi Pulihkan Menu.

5. Pengujian yang dilakukan:
   - Chromium: 14 menu admin berisi konten tanpa halaman kosong dan tanpa exception JS.
   - PIN salah -> Perbaiki Input -> PIN benar -> Pengaturan terbuka: PASS.
   - Share arsip menggunakan Gateway Fonnte, tanpa prompt/WhatsApp Web: PASS (mock backend).
   - Pemeriksaan perangkat Fonnte + kuota: PASS (mock backend).
   - Modal Share dibiarkan terbuka lalu Pulihkan Menu tanpa menutup app: PASS.
   - Python unit tests: token invalid, perangkat terputus, kuota gagal, consent,
     duplicate send dan accepted queue: PASS (Fonnte mock).
   - QR sesi PHOTO, Google Drive upload mock, dan retensi Live Photo: PASS.
   - Node JS --check dan Python compile: PASS.
   - Pengujian Fonnte akun asli dengan token Anda dan Electron/Windows fisik:
     BELUM dapat dilakukan dari lingkungan ini; lakukan lewat menu Periksa Koneksi di booth.

Cara instal:
1. Tutup KACA.ID terlebih dahulu dan backup source v0.9.81.
2. Ekstrak file PATCH dan salin ISI folder patch ke folder utama aplikasi.
3. Ganti file lama, tetapi jangan menghapus AppData, media, konfigurasi, atau token.
4. Jalankan run-kaca-id.bat lalu buka Pengaturan Umum -> Diagnostik Fonnte.
5. Jika perangkat connect dan quota ada, aktifkan pengiriman Fonnte.
6. Uji 1 sesi FOTO percobaan sampai Output & Cetak -> Share WhatsApp.
7. Jika menu/PIN macet, gunakan Perbaiki Input, Pulihkan Menu, atau Ctrl+Alt+R.
