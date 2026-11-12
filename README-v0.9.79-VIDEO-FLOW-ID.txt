KACA.ID v0.9.79 — MODE VIDEO: SLIDE FOTO, HASIL AKHIR, QR, WHATSAPP
===================================================================
BASIS TEKNIS: KACA.ID v0.9.78 EVENT LOCAL + GOOGLE DRIVE + QR.
Ini adalah cabang pembaruan MODE VIDEO, BUKAN paket untuk cabang cloud monitoring
v0.9.79 terpisah. Jangan timpa source cloud monitoring dengan patch ini.

YANG BERUBAH
1. MODE VIDEO sekarang mengikuti UI SESSION PHOTO:
   - Stage transaksi (voucher/QRIS) ketika aktif, atau dilewati bila nonaktif.
   - Pilih frame (termasuk frame khusus Event); semua frame dimuat sebelum lanjut.
   - Preview kamera fullscreen dan tombol Mulai Rekam, Hentikan & Tinjau,
     Balik Preview (mirror), dan Keluar.
   - Review rekaman dengan Ulangi Video dan Lanjut ke Hasil.
   - Slide Hasil Akhir dua media seukuran: poster frame pertama (kiri)
     dan video autoplay loop muted tanpa play/pause (kanan), QR sesi video,
     kontak WhatsApp, email, unduh MP4, tombol Selesai dan countdown.
2. Setiap VIDEO selesai direkam, MP4 disimpan segera ke lokal.
   Sesi VIDEO Event masuk ke Events/Event_<ID>/Video_Results/.
   Sesi VIDEO umum masuk ke Video_Results/ seperti sebelumnya.
   Rekaman memiliki metadata dan poster JPEG. Frame PNG terpilih dan mirror
   diterapkan pada output yang direkam, bukan hanya tampilan kamera.
3. Upload video MP4 ke Google Drive masuk antrean secara asynchronous.
   Folder per-video dibuat sebelum upload besar dimulai, dan QR menunjuk
   folder per-video tersebut, bukan keseluruhan Event. QR dapat tersedia
   sambil video masih diunggah. Penerima perlu menunggu MP4 masuk folder.
   Semua akses bergantung pada koneksi Drive, izin berbagi dan internet.
4. Preview operator memakai video WebM VP8/VP9 yang dirender dari MP4 lokal.
   Berkas MP4 asli tetap diunggah tanpa diganti GIF. Jika encoder WebM tidak
   tersedia, hasil lokal MP4 tidak hilang; preview bisa gagal pada Electron.
5. WhatsApp: mode Fonnte mengirim link tanpa membuka WhatsApp jika token valid
   dan user menyetujui pesan. Click-to-Chat dan WhatsApp Cloud lama tetap ada.
   Respons accepted dari gateway bukan bukti pesan sudah sampai.

INSTALASI PATCH (UNTUK v0.9.78)
1. Tutup aplikasi KACA.ID dan backend Python hingga tidak ada proses aktif.
2. Backup folder source aplikasi dan seluruh AppData/Pictures KACA STUDIO.
3. Ekstrak patch dan salin ISI folder KACA-ID-v0.9.79-VIDEO-PATCH ke root
   aplikasi v0.9.78 yang berisi package.json, lalu Replace file lama.
4. Jalankan run-kaca-id.bat. Uji transaksi/video/frame/QR dengan data percobaan.
5. Jika memakai cabang CLOUD ADMIN dari percakapan lain, jangan langsung
   gunakan patch ini; perlu penggabungan source agar fitur cloud tetap ada.

PENGUJIAN PEMBUATAN
- Browser Chromium headless mode transaksi ON/OFF, pilih frame, rekam,
  hentikan, review, final video autoplay, QR dan WA Fonnte simulasi: LULUS.
- Ukuran bidang poster dan video saat hasil akhir: IDENTIK (uji 1440x900).
- Backend Python/OpenCV dengan kamera simulasi: frame tertanam pada MP4,
  rekaman MP4 lokal, poster, WebM preview, Drive job, QR per-video: LULUS.
- GET video WebM Range request HTTP 206: LULUS.
- Regresi PHOTO QR, Drive mock, Event storage dan DOKU/Fonnte: LULUS.
- Perangkat asli Windows, kamera Canon, akun Drive dan WhatsApp sungguhan:
  BELUM DIUJI karena hardware/kredensial tidak tersedia pada pengembangan.
