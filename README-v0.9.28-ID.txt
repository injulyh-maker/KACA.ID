KACA.ID Photobooth v0.9.28

PENGEMBANGAN UTAMA
1. Advanced UI Designer kini menampilkan struktur layar aplikasi KACA.ID yang menggunakan komponen HTML/CSS aktual (Dashboard, Preview Sesi, Pemilihan Frame, Filter, dan Slide Hasil), bukan mockup blok generik. Pilih komponen langsung pada kanvas, geser untuk mengubah posisi, tarik handle sudut untuk ukuran, lalu atur warna, transparansi, dan skala. Pratinjau memakai konten contoh pada area yang membutuhkan kamera/foto pelanggan; perubahan disimpan sebagai tema dan diterapkan pada selector layar terkait.
2. Integrasi Google Drive menggunakan OAuth 2.0 Desktop App dan Google Drive API. Hasil foto sesi disimpan lokal terlebih dahulu ke folder Sesi_YYYYMMDD_NNN, lalu diunggah secara asinkron dengan struktur Photos, Live_Photos, Final_Results, dan Session_Info.json. Video standalone diunggah ke folder Video_<ID>/Video_Results. File besar menggunakan resumable upload 8 MB per potongan.
3. Link folder Google Drive dibuat setelah unggahan selesai. Folder sesi diberi izin anyone-with-the-link viewer bila kebijakan akun Google mengizinkan. Status unggahan disimpan; ketika offline/kegagalan jaringan, antrean persisten mencoba ulang otomatis hingga batas percobaan, dan operator dapat menjalankan Coba Ulang Antrean Upload.
4. Pengaturan Umum menambahkan konfigurasi OAuth Client ID/Client Secret, Hubungkan, Putuskan, dan Coba Ulang. Client Secret disimpan lokal di komputer booth pada data aplikasi, bukan dikirim ke server pihak ketiga selain endpoint OAuth Google.
5. Arsip sesi menampilkan status dan tautan Google Drive. Halaman hasil menampilkan tautan ketika unggahan selesai. Video standalone menampilkan tautan setelah upload selesai.
6. Jalur Canon EDSDK utama, worker, native binding, dan DLL tidak diubah oleh pengembangan ini.

PERSIAPAN GOOGLE DRIVE
1. Buka https://console.cloud.google.com/ dan buat/pilih project Google Cloud.
2. Aktifkan Google Drive API untuk project tersebut.
3. Konfigurasikan OAuth consent screen dan tambahkan akun booth sebagai test user bila aplikasi masih dalam mode Testing.
4. Buat OAuth Client ID dengan tipe Desktop app.
5. Salin Client ID dan Client Secret ke KACA.ID > Pengaturan Umum > Penyimpanan & Berbagi Otomatis Google Drive.
6. Tekan Simpan & Hubungkan Google Drive, masuk ke akun booth di browser, lalu izinkan akses.
7. KACA.ID akan mengunggah hasil baru secara otomatis. Unggahan lama yang menunggu otorisasi dapat dimasukkan ulang dari tombol Coba Ulang Antrean Upload.

Catatan berbagi:
- Aplikasi meminta izin drive.file dan membuat folder KACA STUDIO pada Drive akun yang terhubung.
- Tautan folder dibuat dengan izin anyone/reader agar pelanggan dapat membukanya tanpa login. Kebijakan Google Workspace atau administrator dapat melarang berbagi publik; bila itu terjadi, upload tetap selesai tetapi aplikasi menampilkan peringatan akses dan tautan mungkin hanya dapat dibuka oleh akun yang diizinkan.
- OAuth Client Secret disimpan pada folder data aplikasi lokal. Gunakan akun booth khusus dan lindungi akses Windows.
- KACA.ID tidak dapat membuat OAuth Client ID milik pengembang secara otomatis; kredensial Google Cloud harus disediakan oleh pemilik booth.

BUILD WINDOWS
1. Ekstrak source ZIP.
2. Pastikan Node.js LTS dan Python 3.10–3.12 tersedia.
3. Jalankan build-windows-installer.bat.
4. Target installer: dist\KACA-ID-Setup-0.9.28-x64.exe.
5. Setelah instalasi, jalankan setup-python.bat sekali bila Python/OpenCV belum tersedia.

PENGUJIAN OTOMATIS YANG DILAKUKAN
- node --check main.js, preload.js, src/app.js.
- python -m py_compile backend/camera_server.py backend/google_drive.py.
- tests/google_drive_test.py: OAuth state/URL, konfigurasi token, folder Drive, resumable upload dengan mock HTTP (tanpa akun/network Google nyata).
- tests/smoke_test.py: slot duplikat, komposisi output, arsip lokal, MP4, dan controller Canon tiruan.
- tests/v0926_video_test.py: HTTP start/stop rekaman pada Angle 1 dan Angle 2 dengan frame sintetis.
- ZIP integrity dan sinkronisasi src.zip.

BATAS PENGUJIAN
- OAuth nyata, upload Google Drive ke akun sungguhan, izin berbagi publik, serta pemulihan jaringan belum diuji dengan kredensial Google milik pengguna.
- Canon EOS 1300D, printer Windows, dan touchscreen tidak diuji secara fisik pada lingkungan ini.
- Installer EXE tidak dibuat di lingkungan Linux; buat pada Windows menggunakan batch build di atas.


PENGEMBANGAN BARU v0.9.28 — WHATSAPP CLOUD API
1. Tombol Kirim WhatsApp Otomatis dan tombol Share pada Arsip Sesi mengirim pesan langsung dari backend melalui WhatsApp Business Cloud API resmi Meta. Tidak membuka WhatsApp Web/Desktop. Pengiriman video standalone juga dapat dimasukkan ke antrean Cloud API.
2. Pengiriman disimpan dalam antrean lokal yang persisten. Jika upload Google Drive belum selesai, pesan menunggu sampai folder sesi siap dan tautannya sudah tersedia.
3. Satu pesan template Utility dikirim dengan link folder Google Drive sebagai variabel {{1}}. Folder sesi PHOTO berisi foto original tanpa filter, foto edited/frame, hasil frame JPG, Live Photo MP4 dalam frame, GIF gabungan foto original, ZIP arsip, dan Session_Info.json. Video standalone dikirim dengan link folder video hasil upload.
4. Nomor telepon dinormalisasi ke format internasional Indonesia (08... menjadi 628...). Pengiriman ganda untuk sesi dan nomor yang sama dicegah.
5. Pelanggan wajib menyetujui penerimaan pesan sebelum operator menekan tombol kirim. Status antrean dan ID pesan Meta ditampilkan pada layar hasil. Pesan yang gagal dapat dicoba ulang.

PERSIAPAN WHATSAPP CLOUD API
1. Siapkan WhatsApp Business Platform / Cloud API melalui Meta for Developers dan tambahkan nomor bisnis.
2. Siapkan Phone Number ID dan Access Token yang memiliki izin whatsapp_business_messaging.
3. Buat template pesan kategori Utility di WhatsApp Manager dan tunggu sampai status Approved.
4. Isi template dengan tepat satu variabel teks {{1}} pada bagian BODY. Contoh:
   Terima kasih telah menggunakan KACA.ID. Hasil photobooth sesi Anda sudah tersedia.
   Buka dan unduh seluruh hasil melalui tautan berikut: {{1}}
5. Buka KACA.ID > Pengaturan Umum > Pengiriman Hasil Otomatis melalui WhatsApp. Masukkan Phone Number ID, Access Token, Graph API Version (default v26.0), nama template, dan bahasa template (misalnya id), lalu simpan.
6. Pada layar hasil sesi, masukkan nomor pelanggan, pastikan persetujuan telah diberikan, lalu tekan Kirim WhatsApp Otomatis. KACA.ID akan menunggu upload Google Drive selesai sebelum mengirim pesan.

CATATAN WHATSAPP DAN PRIVASI
- Bisnis wajib memiliki opt-in pelanggan yang sesuai sebelum mengirim pesan WhatsApp. Checkbox pada layar hasil adalah konfirmasi operator bahwa persetujuan tersebut telah diberikan.
- Untuk memulai percakapan bisnis, gunakan template yang disetujui Meta. Pesan bebas hanya diperbolehkan dalam jendela layanan pelanggan 24 jam setelah pelanggan mengirim pesan kepada bisnis.
- Meta dapat mengenakan biaya sesuai kategori template dan kebijakan harga yang berlaku.
- Status sent berarti API Meta menerima pesan dan mengembalikan ID wamid; status delivered/read memerlukan webhook WhatsApp yang belum disertakan pada versi ini.
- Access Token disimpan lokal di folder data aplikasi sebagai teks biasa. Lindungi akun Windows booth dan jangan membagikan file konfigurasi atau token. Jangan mengirim token melalui chat.

PENGUJIAN TAMBAHAN v0.9.28
- python -m py_compile backend/camera_server.py backend/google_drive.py backend/whatsapp_cloud.py.
- tests/whatsapp_cloud_test.py: konfigurasi token lokal, validasi konfigurasi, normalisasi nomor Indonesia, dan payload template Cloud API dengan HTTP mock.
- Canon EDSDK utama, worker, native binding, dan DLL dibandingkan dengan source v0.9.26; seluruh file tetap identik.

BATAS PENGUJIAN TAMBAHAN
- Pengiriman WhatsApp nyata belum diuji karena Phone Number ID, Access Token, dan template Meta milik pemilik booth belum tersedia.
- Google Drive upload/share nyata tetap memerlukan OAuth Client ID/Secret milik pemilik booth.
