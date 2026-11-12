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
