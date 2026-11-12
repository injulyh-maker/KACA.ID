KACA.ID v0.9.56 — CAMERA ORIENTATION & PREVIEW QUALITY

Perubahan:
1. Preview frame pada slide Pilih Filter diperkecil secara proporsional agar tetap berada di dalam kolom preview.
2. Pengaturan kamera baru: rotasi 0/90/180/270 derajat, flip horizontal, dan flip vertikal.
3. Transformasi kamera diterapkan pada tampilan live, foto sesi yang disimpan, dan Live Photo.
4. Pengaturan live preview terpisah: kualitas JPEG preview 50–92, brightness tampilan 70–130%, dan FPS 5–30.
5. Kualitas preview hanya mengatur stream MJPEG. Brightness hanya CSS pada renderer. Keduanya tidak mengubah foto hasil.
6. Penyimpanan still memakai kualitas JPEG sesuai pengaturan, default baru 100, tanpa resize pada frame yang diterima backend.
7. Folder sesi lokal tetap menjadi sumber unggahan Google Drive sehingga file yang diunggah adalah file yang sama dengan arsip lokal.

PENTING — BATASAN KAMERA CANON:
Canon EDSDK pada source ini mengirim perintah shutter, tetapi belum menerima transfer JPEG/RAW resolusi penuh dari kamera. Saat ini foto Canon masih diambil dari frame Live View. JPEG quality 100 menghindari kompresi tambahan yang lebih besar, tetapi bukan file asli DSLR dan bukan lossless. Implementasi transfer file EDSDK penuh perlu tahap tersendiri sebelum dapat menjamin resolusi/bit-depth/quality persis seperti pengaturan kamera.

Build:
- Extract source ke folder baru.
- Jalankan setup.bat.
- Jalankan npm.cmd run dist:win pada Windows.

Validasi:
- Syntax JavaScript dan kompilasi Python diuji.
- Tes otomatis proyek dijalankan; hasilnya dicatat dalam laporan rilis.
- Kamera fisik, Canon EOS, webcam, printer, dan unggahan Drive nyata belum diuji pada perangkat pengguna.
