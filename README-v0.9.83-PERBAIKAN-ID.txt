KACA.ID v0.9.83 — PENGATURAN, CETAK QR, FONNTE
===================================================
BASIS: KACA.ID v0.9.82 FULL SOURCE (bukan v0.9.79 CLOUD ADMIN).

1. FONNTE
- Perbaikan pesan: "Halo, kami dari KACA.ID Photobooth Studio 😊" plus ucapan terima kasih dan tautan Drive sesi yang benar.
- Ketika menyimpan token baru, KACA.ID memeriksa POST https://api.fonnte.com/device lebih dulu sebelum menimpa token lama.
- Fonnte memerlukan token PERANGKAT yang tersedia di menu Devices pada dashboard Fonnte (bukan nomor WA atau account token di menu Settings).
- Bila Fonnte mengembalikan "invalid token", aplikasi tidak dapat mengirim sampai token valid disimpan. Data token lama tidak dibagikan dan tidak tercantum dalam ZIP.
- Status diterima gateway bukan bukti pesan sudah tiba di WhatsApp pelanggan.

2. QR GOOGLE DRIVE UNTUK CETAK FRAME
- Saat QR di Frame & Layout diaktifkan, hasil cetak dibuat menjadi output_print_qr.jpg.
- output.jpg digital tetap tanpa perubahan; foto original juga tetap tidak dimodifikasi.
- QR diproses saat folder Drive selesai disiapkan ataupun setelah output JPG dirender.
- Cetak menunggu URL sesi dan JPG QR tersedia jika fitur QR cetak aktif; jika tidak, API mengembalikan status 409 dengan alasan yang jelas (tidak mencetak tanpa QR secara diam-diam).
- Hasil_Frame_Dengan_QR.jpg juga disalin ke arsip lokal dan antrean Google Drive saat tersedia.

3. PENGATURAN UMUM
Submenu: Umum; Share File; Kamera & Video; App Logs.
Umum: Lokasi Penyimpanan Lokal dan Penyimpanan & Berbagi Otomatis Google Drive.
Share File: Metode WhatsApp, WhatsApp Cloud API, Mode Dasbor, Gateway Fonnte, Diagnostik Fonnte.
Kamera & Video: Kamera, kualitas foto/video/cetak, flip/orientasi, live preview, kontrol profesional.
App Logs: Catatan Permasalahan.
- Pindah submenu tidak membuat ulang kontrol yang ada, sehingga fungsi simpan dan tombol terkait tetap bekerja.
- Pilih kamera Angle 1 / 2 akan langsung memulai stream preview jika kamera tersedia.
- Kontrol profesional ditempatkan di bawah setiap preview dan hanya aktif bila OpenCV/driver bisa membaca propertinya. Penggunaan nilai akan divalidasi lagi saat dikirim ke driver.
- Untuk DSLR Canon EDSDK, kontrol ISO/shutter OpenCV tidak dipalsukan sebagai kontrol tersedia. Atur di bodi kamera sampai driver/SDK khusus mendukungnya.
- Flip, rotasi, kecerahan preview, FPS dan kualitas tampilan langsung terlihat/berlaku pada preview.

4. PAGINATION
- Voucher, Output & Cetak, Arsip Sesi maksimal 10 baris/sesi per halaman.
- Navigasi Kembali, nomor halaman, Lanjut.

5. CETAK
- Pengaturan Sesi: pilihan Tambah Cetak dan batas salinan, serta Cetak Otomatis.
- Tambah Cetak membuka pilihan jumlah cetak dari 1 sampai maksimum admin.
- Cetak Otomatis mengunci tombol cetak slide hasil, menunggu foto/QR siap, dan mencatat keberhasilan pada manifest untuk mencegah cetak ulang yang tidak disengaja.
- Jika printer rusak/belum dipilih, hasil akan menampilkan pesan error, tidak mengklaim cetak berhasil.
- Eksekusi printer nyata membutuhkan Windows dan driver printer; hanya pengujian spooler tiruan yang dilakukan dalam pengembangan ini.

6. TAMPILAN DASHBOARD
- Hapus Logo Dasbor tanpa menghapus file sumber.
- Logo/judul yang ditentukan pengguna berada di sudut kiri atas dashboard.
- Judul "KACA Studio" dapat diedit menggunakan input Tulisan di Pengaturan Tampilan.
- Warna pengaturan dan editor visual ditampilkan sebagai swatch kotak berisi warna yang dipilih.

PENGUJIAN OTOMATIS PENGEMBANGAN
- Chromium: submenu Umum/Share File/Kamera & Video/App Logs; kamera auto preview simulasi; voucher/output paging; cetak tambahan; warna/logo/judul: LULUS.
- Backend HTTP: QR yang belum siap dicegah, QR cetak dipakai setelah siap, 3 salinan, satu cetak otomatis per sesi: LULUS DENGAN PRINTER SIMULASI.
- QR hasil cetak 4R/2R yang dicetak ke JPEG dapat dibaca oleh OpenCV: LULUS.
- Fonnte: pesan pembuka, link Drive, validasi device token dan perlindungan token lama: LULUS DENGAN API SIMULASI.
- QR PHOTO, arsip Event, Google Drive mock, retensi: LULUS.
- Kamera DSLR/webcam fisik, Fonnte nyata, printer Windows asli, dan upload Google Drive nyata: BELUM DIUJI PADA PERANGKAT PELANGGAN.

CARA PASANG PATCH
1. Tutup semua proses KACA.ID. Backup aplikasi v0.9.82 dan folder AppData/Pictures berisi data operator.
2. Ekstrak PATCH, lalu salin ISI folder KACA-ID-v0.9.83-PATCH ke folder utama source v0.9.82 (sejajar package.json).
3. Replace file lama ketika diminta. Jangan menghapus folder data/userData, hasil sesi, atau konfigurasi Drive/Fonnte.
4. Jalankan run-kaca-id.bat. Buka Pengaturan Umum dan konfigurasi printer/Fonnte sesuai perangkat.
5. Uji perangkat nyata sebelum digunakan pada event pelanggan.

PENTING
Token Fonnte tidak dapat dibuat otomatis dari nomor WhatsApp. Ambil token perangkat yang benar dari dashboard Fonnte -> Devices -> Token. Simpan melalui menu Gateway Fonnte, lalu Periksa Koneksi & Kuota.
Dokumentasi: https://docs.fonnte.com/token-api-key/ , https://docs.fonnte.com/api-device-profile/
