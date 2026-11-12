KACA.ID v0.9.55 — PERFORMANCE STAGE A/B

Perubahan:
- General Settings tidak lagi menunggu jeda pemindaian kamera 1,8 detik. Status Drive dan pemicu scan kamera diminta paralel.
- Render Frames memeriksa token navigasi agar hasil API lama tidak menimpa halaman yang lebih baru.
- Preview filter memakai thumbnail JPEG 640x480 kualitas 72 yang dicache di data lokal, bukan mengunduh foto original resolusi penuh.
- Semua thumbnail dimuat paralel dan renderer memakai revision guard agar hasil render lama tidak menimpa pilihan terbaru.
- Foto original dan output final tidak diubah; thumbnail hanya untuk preview UI.

Catatan: tahap ini belum mengubah writer video/camera pipeline karena perlu refactor antrean writer dan pengujian perangkat fisik tersendiri.
