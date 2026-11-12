# KACA.ID Photobooth v0.9.25 — Pengembangan UI, Video, Printer & MultiCam

## Fitur v0.9.25
- Theme Designer lanjutan: warna aplikasi, panel, teks, border, transparansi preview/hasil, ukuran dan posisi preview, ukuran/posisi logo, skala/posisi tombol, skala kartu frame/filter, serta ukuran slide hasil.
- Dashboard memiliki pilihan mode **PHOTO** dan **VIDEO**. Mode video merekam dari kamera aktif, berhenti otomatis sesuai durasi yang diatur di Pengaturan Umum (5–300 detik), menampilkan preview hasil MP4, dan menyediakan unduhan serta tombol berbagi WhatsApp/email.
- Printer & Kertas: tombol **Properties Printer Windows** membuka dialog properti driver Windows. Setelah dialog ditutup, KACA.ID membaca ulang daftar ukuran kertas dan opsi borderless. Ukuran driver yang dipilih diteruskan ke proses cetak.
- Sidebar navigasi pengaturan tetap sticky saat panel kanan digulir.
- MultiCam: tombol deteksi per slot memindai webcam/kamera bawaan dan Canon EOS USB melalui EDSDK. Canon dapat digunakan sebagai Angle 1 atau Angle 2. Untuk Angle 2, backend menjalankan worker EDSDK terpisah; shutter Canon Angle 2 juga diarahkan ke controller yang benar.

## Cara menjalankan dan membangun
1. Ekstrak ZIP sumber lengkap.
2. Pastikan Node.js LTS dan Python 3.10–3.12 x64 tersedia.
3. Jalankan `build-windows-installer.bat` pada Windows 10/11 x64 dengan koneksi internet.
4. Jalankan `setup-python.bat` pada folder aplikasi terpasang jika runtime Python/OpenCV belum disiapkan.
5. Buka KACA.ID Photobooth.

## Catatan pengujian dan batasan
- Pemeriksaan sintaks JavaScript/Python, smoke test komposisi foto dan arsip, serta uji perekaman video dengan frame sintetis dijalankan pada lingkungan pengembangan.
- MultiCam Canon Angle 2 diuji pada level lifecycle dengan controller tiruan; koneksi USB/EDSDK fisik, dua kamera aktif bersamaan, shutter fisik, dan stabilitas jangka panjang tetap perlu diuji pada Windows dengan Canon EOS.
- Dialog Properties printer, ukuran kertas nyata, borderless, dan hasil cetak hanya dapat diverifikasi pada Windows dengan driver printer terpasang.
- File installer `.exe` tidak dibuat pada lingkungan Linux ini. Build installer harus dijalankan di Windows menggunakan batch file di atas.
- Jalur Canon utama yang sebelumnya stabil pada EOS 1300D tidak diubah; file EDSDK inti dan DLL tetap dipertahankan.
