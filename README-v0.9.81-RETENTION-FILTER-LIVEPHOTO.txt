KACA.ID v0.9.81 — Retensi Otomatis, Filter Frame, Durasi Live Photo
==============================================================
Basis: v0.9.80 Startup Dashboard / PHOTO+VIDEO / Event / Google Drive.

1. OUTPUT & CETAK — HAPUS OTOMATIS
   - Pengaturan lokal dan Google Drive TERPISAH (1-3650 hari).
   - Kedua opsi NONAKTIF secara default. Tidak ada data lama yang tiba-tiba
     terhapus setelah pemasangan, kecuali administrator mengaktifkannya.
   - Masa simpan dihitung dari tanggal/jam sesi selesai menurut komputer booth.
   - Setelah dipilih dan disimpan, pemeriksaan berjalan 20 detik setelah aplikasi
     dibuka serta setiap 15 menit selama aplikasi aktif; tombol
     "Periksa Kedaluwarsa Sekarang" juga tersedia.
   - Lokal: file FOTO, Live Photo, ZIP, dan VIDEO di bawah arsip KACA dihapus
     permanen; manifest minimal dipertahankan agar retensi cloud tetap terpisah.
   - Google Drive: hanya folder sesi dan folder video milik KACA yang dapat
     diverifikasi sebagai anak langsung folder KACA STUDIO/Event yang
     dipindahkan ke Sampah (Trash), bukan folder utama Event atau root.
   - Sesi yang sudah dihapus lokal tidak ditampilkan lagi dalam Arsip aplikasi.
     Tautan dan QR Drive yang terhapus dinonaktifkan.
   - Jika antrean upload belum selesai, penghapusan lokal ditunda untuk
     mencegah kehilangan file yang belum dikirim ke Drive. Lihat pesan error
     pada ringkasan pemeriksaan, lalu sambungkan kembali Drive.
   - Pengaturan dan data event, frame PNG, lisensi, dan perangkat tidak dihapus.
   - File di luar folder arsip KACA tidak disentuh; jika lokasi penyimpanan
     lama telah berubah, hapus manual setelah Anda memeriksanya.

   CONTOH: Lokal aktif 7 hari; Drive aktif 30 hari. Pada hari ke-8 file
   lokal hilang dari aplikasi, sedangkan folder Drive tetap tersedia sampai
   penghapusan ke Sampah pada hari ke-30.

   PERINGATAN: Penghapusan lokal permanen. Pencatatan Drive Trash memungkinkan
   pemulihan lewat Google Drive selama sampah belum dikosongkan/otomatis habis.
   Simpan backup dan hanya aktifkan setelah menguji satu sesi.

2. FILTER PADA SLIDE FILTER
   - Daftar foto di samping selalu memakai foto original dari endpoint original.
   - Efek hanya diterapkan ke kanvas komposit foto di dalam frame.
   - Sketsa Pensil/Kartun dari backend tidak ditimpa efek CSS kedua kalinya.
   - Original dalam folder sesi tetap tidak dimodifikasi.

3. LIVE PHOTO
   - Klip sumber yang kekurangan frame ketika countdown ditormalisasi ke
     durasi yang dipilih (contoh 5 detik = 50 frame pada 10 FPS), dengan
     penahanan frame bila kamera tidak mampu mengirim secara konstan.
   - MP4 master dan WebM preview hasil dalam frame divalidasi durasinya.
   - WebM tetap prioritas preview pada slide hasil; tidak memakai GIF.
   - Jika encoding normalisasi gagal, original MP4 tetap disimpan (peringatan
     dicatat), sedangkan perenderan akhir masih menghasilkan durasi target.

PENGUJIAN (lokal, nonproduksi)
  - 8 uji unit retensi/Drive safety/video dan durasi: lulus.
  - HTTP backend save config/expiry/list: lulus.
  - Browser Chromium menu Output & Cetak: lulus.
  - Final Live Photo WebM dan MP4: sama-sama terukur 5,0 detik.
  - QR sesi, folder Drive, dan alur Event regresi: lulus (mock Drive).
  - Belum diuji penghapusan Drive sungguhan, webcam Windows, atau printer fisik.

INSTALASI PATCH
  1. Tutup Electron dan backend Python.
  2. Backup seluruh source KACA.ID v0.9.80 dan folder hasil foto/video.
  3. Ekstrak patch dan salin ISI folder KACA-ID-v0.9.81-PATCH ke root aplikasi
     v0.9.80 (folder yang memuat package.json). Replace file.
  4. Jalankan run-kaca-id.bat. Buka Output & Cetak dan pilih retensi.
  5. Uji pada sesi dummy terlebih dahulu sebelum mengaktifkan retensi produksi.

CATATAN: Patch ini untuk cabang v0.9.80 Startup-Dashboard-No-Frame;
  jika Anda memakai cabang Cloud Admin yang berbeda, perlu merge terpisah.
