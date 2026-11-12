KACA.ID v0.9.77 — MENU SETTINGS & MANAJEMEN EVENT
===============================================
Berbasis FULL SOURCE v0.9.76. Tidak mengubah integrasi QRIS DOKU, QR Google Drive,
pemutaran Live Photo WebM→MP4, atau pengiriman WhatsApp yang sudah tersedia.

A. APA YANG DIPERBAIKI
- Semua navigasi menu Pengaturan menampilkan panel "Memuat..." dan bila gagal
  menampilkan penyebab serta tombol "Coba Muat Ulang", bukan halaman kosong.
- Pengaturan umum ditulis atomik dan mempunyai cadangan kaca-settings.json.bak.
- Bug HTTP 400 saat upload frame PNG (shadowing variabel base64 pada backend) diperbaiki.
- Menambahkan menu baru: "Manajemen Event".
- Data event disimpan terpisah di userData/kaca-events.json dan tidak menimpa
  pengaturan umum (userData/kaca-settings.json).
- Frame event memiliki pemilik event_id pada metadata backend. Frame event tidak
  tampil pada daftar frame umum atau event lain.
- Sesi foto disimpan dengan event_id/event_name; menu Arsip Sesi dan Output & Cetak
  menyaring sesi berdasarkan event aktif. Berkas hasil tetap di mekanisme arsip
  lokal/Drive lama untuk menghindari regresi QR dan upload.
- Setiap event dapat mengatur nama, tanggal, kategori, ukuran kertas/cetak,
  orientasi, ukuran custom, jumlah salinan, frame PNG, mode PHOTO, mode VIDEO,
  dan Live Photo.
- Mode VIDEO/PHOTO yang tidak diaktifkan event tersembunyi dari dashboard.
- Nomor identitas akun Fonnte +62 823-9667-4553 muncul di Pengaturan Umum.
  Nomor dapat diedit. Token API tetap harus ditambahkan secara manual.

B. PEMASANGAN
1. Tutup KACA.ID, proses Electron, dan backend Python yang berjalan.
2. Backup folder source lama (v0.9.76) dan data userData KACA.ID sebelum patch.
3. Ekstrak paket patch lalu salin ISI folder KACA-ID-v0.9.77-PATCH ke
   folder utama KACA.ID v0.9.76 tempat package.json berada.
4. Saat Windows meminta konfirmasi penggantian file, pilih Replace.
5. Jalankan run-kaca-id.bat seperti biasa. Jangan hapus folder media, data sesi,
   maupun pengaturan printer/kamera.

C. CARA MEMBUAT EVENT
1. Masuk ke Manajemen Event → Tambahkan Event; isi contoh "Wedding Aldi & Diah".
2. Klik Atur, pilih 4R / 2R Strip / Custom, orientasi dan jumlah cetak.
3. Unggah frame PNG transparan maksimal 15 MB; pilih sebagai frame utama.
4. Aktifkan PHOTO, VIDEO, dan Live Photo sesuai kebutuhan.
5. Klik Simpan Pengaturan Event → Aktifkan Event Ini.
6. Jika ingin mengatur slot foto frame secara presisi, buka Frame & Layout setelah
   Event aktif, lalu simpan layout event tersebut.
7. Untuk kembali ke konfigurasi umum, Manajemen Event → Kembali ke Mode Umum.

D. FONNTE
- Nomor akun Fonnte ditampilkan sebagai identitas, BUKAN token API.
- Ambil token API dari dashboard Fonnte pada perangkat yang Anda hubungkan.
- Masuk Pengaturan Umum → Gateway Fonnte, masukkan token dan simpan.
- Pilih mode Gateway Fonnte sebagai metode pengiriman.
- Pengiriman asli memerlukan internet, layanan Fonnte aktif, perangkat WA
  terhubung, serta persetujuan penerima. Pengujian pengiriman WA nyata tidak
  dilakukan karena token akun tidak diberikan.

E. PENGUJIAN TEKNIS
- Browser Chromium dengan respons backend simulasi: 14 menu admin memuat
  isi tanpa blank/error JavaScript.
- Event dibuat, diaktifkan, disimpan sebagai 2R Strip + VIDEO nonaktif, lalu
  dinonaktifkan: konfigurasi umum 4R + VIDEO aktif pulih.
- Saat backend frame dibuat gagal: panel error dan tombol Coba Muat Ulang muncul.
- Backend Python nyata dengan data sementara: upload PNG event + PNG umum berhasil,
  masing-masing memiliki metadata event_id yang benar dan tidak tercampur.
- Pemeriksaan sintaks JS dan Python lulus.
- Belum diuji dengan hardware Canon/Windows, printer asli, token Fonnte asli,
  atau transaksi QRIS asli pada komputer booth pelanggan.

F. CATATAN KEAMANAN DATA
- Event hanya memisahkan pengaturan, penampilan frame dan daftar sesi di UI.
  File hasil fisik masih memakai mekanisme arsip lokal dan Drive per sesi yang
  sudah ada. Event yang dihapus tidak otomatis menghapus foto atau hasil lama.
- Buat backup terlebih dahulu sebelum pemasangan update dan sebelum build installer.
