KACA.ID v0.9.36 — MultiCam stability and filter preview repair

Perubahan:
- Reuse kamera kedua yang sudah aktif agar tidak memutus dan membuka ulang DirectShow/Canon EDSDK saat sesi dimulai.
- Validasi awal sesi mengikuti angle kamera yang dipilih.
- Tombol ANGLE 1/ANGLE 2 dipindahkan ke kiri bawah preview; tombol Ambil Foto tetap di tengah bawah dan Mirror di kanan bawah.
- Preview still/live pada Atur Nuansa Foto dibatasi agar proporsinya tetap utuh.
- Live Photo preview mencoba autoplay saat mode LIVE PHOTO dipilih dan output tersedia.
- Area pemilihan foto untuk slot diperpanjang.

Canon/EDSDK tidak dimodifikasi. Pengujian kamera fisik tetap harus dilakukan pada PC booth.
