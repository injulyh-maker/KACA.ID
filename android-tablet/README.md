# KACA.ID Android Tablet — versi beta, bukan port Electron 1:1

Android tidak bisa menjalankan `camera_server.py` Windows, Canon EDSDK, printer desktop, atau Electron.
Maka proyek ini adalah aplikasi Android **native beta** terpisah yang mendukung:

- aktivasi melalui HTTPS `https://kacastudio.id`, memakai akun terverifikasi dan satu lisensi untuk satu tablet;
- verifikasi Ed25519 lisensi yang mengikat device ID dan masa kedaluwarsa tanpa internet;
- pengambilan foto menggunakan aplikasi kamera Android, penambahan satu overlay frame PNG yang dipilih pelanggan;
- penyimpanan asli dan hasil JPG di Pictures/KACA-ID, serta antrean metadata sesi offline yang dikirim ke Cloud.

**Belum setara dengan Windows**: live photo WEBM, DSLR, strip multiphoto/frame-slot editor, QR Drive, QRIS, Fonnte, printing, mode video, remote screen, dan kemampuan sinkronisasi file media lintas perangkat tidak ada di beta ini. Tampilan juga berbeda dari UI Windows.

Build via GitHub Actions > `KACA.ID - Android Tablet APK (beta)` > Run workflow. File `app-debug.apk` hanya untuk pengujian privat, bukan installer rilis publik. Build publik membutuhkan penandatanganan release keystore, audit, serta pengujian pada tablet Android asli. 

Perangkat harus memiliki Android 13+ (API 33). Kamera Android bawaan menangani capture. Jangan menggunakan lisensi Windows yang sudah terikat pada perangkat lain.


## v0.9.92 beta — responsif & perangkat

- Menu Pengaturan Umum menggunakan kategori Kamera, Sesi, Printer, Suara, dan Cloud; halaman utama dapat di-scroll sendiri pada portrait dan landscape. Sidebar juga scroll independen.
- Android Print Framework menghasilkan dokumen PDF foto 4R (4x6 inci), 2R standar (2,5x3,5 inci), atau 2R Strip (2x6 inci), dengan pilihan Fit/Fill. Dialog Print Service Android memilih printer. Tidak ada jaminan printer fisik muncul atau menerima media khusus tanpa driver/Print Service yang kompatibel.
- Pemindaian perangkat memeriksa Android Camera2 internal/eksternal dan kamera USB UVC/PTP via USB OTG. DSLR PTP hanya terdeteksi: shutter jarak jauh, Live View, RAW, dan Canon EDSDK Windows **tidak otomatis didukung**.
- Countdown dan cekrek bisa disetel on/off dan custom audio lokal; pengenalan suara bahasa Indonesia bergantung TTS Android/WebView.
- Foto hasil dapat dibagikan dan dicetak melalui layanan Android; sesi lisensi offline dan sinkronisasi metadata Cloud tetap menggunakan implementasi lama.

**Batas kesetaraan:** belum tersedia pada Android: Canon/Nikon DSLR shutter/Live View terintegrasi, Google Drive media/QR dalam frame, Fonnte, sistem filter OpenCV lengkap, pencetakan otomatis tanpa dialog, dan remote-control desktop Windows. APK tidak boleh dinyatakan identik secara fungsional dengan Windows. Uji pada model Android, kamera, printer, dan Print Service yang ditargetkan wajib dilakukan sebelum rilis pelanggan.
