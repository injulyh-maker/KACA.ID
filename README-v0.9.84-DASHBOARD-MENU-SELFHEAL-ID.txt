KACA.ID v0.9.84 — LOGO DASHBOARD & OTOMATIS PULIHKAN MENU
========================================================

BASIS: Full Source KACA.ID v0.9.83 QR/Fonnte/Settings/Print.

DASHBOARD
- Logo dashboard saja yang berada di kiri atas.
- Judul KACA Studio / judul yang diedit operator tetap di tengah atas
  (di atas area preview kamera), tidak mengikuti posisi logo.
- Perbaikan dilakukan pada susunan elemen dashboard dan CSS khusus dashboard.
- Logo yang belum diunggah tidak menampilkan elemen kosong.

PEMERIKSAAN KEUTUHAN MENU
- Setiap navigasi admin merender menu, menunggu browser menyelesaikan layout,
  kemudian memeriksa tombol/field wajib berdasarkan halaman terkait.
- Pemeriksaan meliputi 14 menu admin + dashboard dan 4 submenu Pengaturan Umum.
- Bila menu hanya memuat sebagian, aplikasi mencoba render ulang secara otomatis,
  hingga total maksimal 3 percobaan pada navigasi tersebut.
- Setelah berhasil, menu dipantau 5,5 detik untuk mendeteksi komponen yang
  hilang belakangan; satu rangkaian pemulihan susulan diperbolehkan.
- Saat Pengaturan Umum berpindah submenu, panel yang seharusnya terlihat
  diperiksa lagi. Bagian yang tetap tersembunyi dianggap gagal render.
- Jika semua percobaan gagal, panel kesalahan menampilkan bagian yang kurang
  beserta tombol Coba Muat Ulang dan Dashboard. Aplikasi tidak loop tanpa batas.
- Bila pengguna sudah mengetik di form yang belum tersimpan, pemulihan otomatis
  ditahan untuk menjaga input; gunakan tombol Coba Muat Ulang bila diperlukan.
- Sesi foto dan video aktif dikecualikan dari render ulang otomatis supaya
  proses pemotretan dan video tidak terhenti.
- Kesalahan keutuhan menu dikirim ke diagnostik renderer/App Logs.

PERBAIKAN VISIBILITAS
- Tinggi dan overflow area menu admin disetel tidak terpotong.
- Panel submenu Pengaturan Umum yang hidden tetap benar-benar tersembunyi,
  sedangkan panel submenu aktif dipastikan terlihat.

PENGUJIAN
- Chromium pada resolusi 1366x768, 1920x1080, 1100x700, 750x800:
  judul dashboard tepat di tengah, logo tetap di sisi kiri atas.
- 14 menu admin dibuka dengan backend simulasi: tidak ada yang kosong.
- 4 submenu Umum / Share File / Kamera & Video / App Logs diuji: lulus.
- Simulasi menghapus tombol wajib: menu terdeteksi rusak dan pulih otomatis.
- Simulasi menu gagal permanen: pesan dan tombol Coba Muat Ulang tersedia.
- Simulasi operator sudah mengisi formulir: input dipertahankan, bukan di-reset.
- Syntax JavaScript, Python dan regresi QR sesi: lulus.
- Belum dilakukan pengujian pada Electron Windows dengan perangkat kamera
  dan Google Drive pelanggan yang sesungguhnya.

INSTALASI PATCH
1. Tutup seluruh proses KACA.ID, lalu backup folder source dan data user.
2. Ekstrak KACA-ID-v0.9.84-PATCH.
3. Salin ISI folder patch ke folder utama aplikasi v0.9.83 yang memiliki
   package.json. Pilih Replace saat diminta.
4. Jalankan run-kaca-id.bat, lalu buka Pengaturan Umum dan submenunya.
5. Bila ada menu yang gagal permanen, tekan Coba Muat Ulang atau Pulihkan Menu.

Data user, token Fonnte, kredensial Drive, arsip, pengaturan Event, dan fitur
cetak tidak dimodifikasi dalam perubahan ini.
