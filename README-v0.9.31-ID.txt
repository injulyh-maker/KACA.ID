KACA.ID v0.9.31 — QR CODE WINDOWS COMPATIBILITY HOTFIX

Perbaikan:
- Pembuatan QR Google Drive tidak lagi menggunakan Pillow/PIL untuk menulis PNG.
- QR dibuat dari matriks paket qrcode dan PNG ditulis memakai modul standar Python (struct dan zlib).
- Menghindari pemuatan DLL Pillow _imaging pada jalur pembuatan QR, termasuk pada Windows dengan path instalasi panjang.
- Pengujian QR memvalidasi struktur PNG dan data piksel tanpa mengimpor Pillow.

Catatan:
- Pillow tetap menjadi dependensi aplikasi untuk operasi gambar/foto lain.
- Perbaikan ini tidak mengubah integrasi Google Drive, WhatsApp, atau Canon EDSDK.
- Google Drive sungguhan, perangkat Canon, dan installer Windows tetap perlu diuji pada komputer operasional.

Upgrade:
Ekstrak full source ke folder baru, jalankan setup.bat, verify-kaca-id.bat, lalu build-windows-installer.bat.
