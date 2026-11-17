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


## v0.9.93 beta - USB/PTP device interoperability

The Android USB Host path now detects the USB Still Image Class with BULK IN/OUT endpoints, requests permission, probes PTP GetDeviceInfo and InitiateCapture capability and, on devices accepting the standard operation, requests a capture, compares object handles and downloads a new JPEG. It never deletes files on the camera. The JPEG is saved to Originals and follows the existing photo frame/results and Cloud session metadata logic. A valid offline license is required to shoot. Capture Studio has a source selector (Android or DSLR USB/PTP), and the Device settings page has PTP probe/shutter test buttons. Connect with USB OTG and configure the camera for PTP mode and JPEG or RAW+JPEG.

Limitations: proprietary Canon/Nikon/Sony vendor operations, camera-specific Live View, manual ISO/shutter/aperture settings, RAW-only capture and MTP interfaces without PTP are not covered. Physical model+firmware tests are essential. USB device IDs may change when reconnected.

Printer detection lists USB Printer Class hardware alongside Android Print Services. Output still uses the Android PrintManager pathway for 4R, 2R standard or 2R strip. USB presence does not establish driver compatibility. For Wi-Fi/USB photo printers install a compatible Android vendor, IPP or Mopria Print Service and confirm the media size in the print dialog.

Do not publish as a 100% feature-parity release without testing the intended camera, printer and tablet. A successful CI build only confirms static checks and compilation.
