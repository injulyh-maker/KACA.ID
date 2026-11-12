KACA.ID v0.9.38 — Perbaikan Live Photo dan Google Drive

Perubahan:
- MP4 master tetap disimpan sebagai output_live.mp4.
- Membuat companion output_live.webm untuk preview Chromium/Electron setelah render frame Live Photo.
- UI preview menggunakan WebM yang benar-benar dihasilkan backend; pesan error preview ditampilkan bila gagal.
- Google Drive tidak mengunggah arsip ZIP maupun Session_Info.json. Keduanya tetap tersedia secara lokal.
- Jalur Canon EDSDK tidak diubah.

Build Windows:
1. Ekstrak source ZIP.
2. Jalankan setup.bat.
3. Jalankan verify-kaca-id.bat.
4. Jalankan npm.cmd run dist:win.

Catatan: preview WebM memerlukan encoder VP8/VP9 yang tersedia pada build OpenCV. Jika encoder tidak tersedia, MP4 master tetap disimpan dan log LIVE_OUTPUT_PREVIEW_WARNING dicatat.
