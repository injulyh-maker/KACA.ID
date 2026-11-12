KACA.ID - PATCH PERBAIKAN SIKLUS HIDUP CANON EDSDK

Isi ZIP:
- backend/canon_edsdk_runtime.py  (modul koordinasi EDSDK bersama)
- backend/canon_edsdk.py          (deteksi Canon tidak menginisialisasi ulang saat Live View aktif)
- backend/canon_edsdk_live.py     (serialisasi init/cleanup SDK dan status sesi aktif)
- backend/camera_server.py       (penguncian buka/tutup kamera; controller tidak dibuang bila thread native belum berhenti)

CARA MEMASANG
1. Tutup KACA.ID sepenuhnya.
2. Buka folder instalasi/source KACA.ID, lalu masuk ke folder backend.
3. Salin folder backend dari ZIP ini ke folder utama KACA.ID dan izinkan Windows mengganti file yang sama.
4. Pastikan file backend/edsdk/EDSDK.dll dan DLL pendamping Canon yang sudah ada TIDAK dihapus atau ditimpa.
5. Jalankan KACA.ID kembali.
6. Deteksi Canon satu kali. Pilih Canon dan tekan Aktifkan Preview.
7. Jangan tekan Uji Shutter sebelum Live View benar-benar menampilkan gambar.

PENTING
- Patch ini memperbaiki konflik lifecycle EDSDK di dalam proses KACA.ID dan mencegah dua permintaan open/close berjalan bersamaan.
- Jika thread EDSDK masih tertahan di native call, aplikasi akan mempertahankan controller dan menolak membuka sesi Canon kedua, alih-alih melepas referensi SDK secara paksa.
- Patch ini belum dapat membuktikan kompatibilitas hardware EOS 1300D tanpa pengujian langsung di komputer/kamera pengguna.
- Transfer JPEG resolusi penuh dari kamera ke folder sesi belum ditambahkan pada patch ini; jalur shutter saat ini tetap mengirim perintah shutter melalui EDSDK.

Jika masalah masih terjadi, kirim log mulai dari proses deteksi Canon sampai pesan pembukaan Live View.

PATCH TAMBAHAN v2 (berdasarkan log 22.16)
- Memperbaiki pemeriksaan signature JPEG pada frame EVF Canon. Sebelumnya kode membandingkan empat karakter literal '\\xff' dan '\\xd8', bukan dua byte JPEG 0xFF 0xD8. Akibatnya frame yang sebenarnya diterima dapat diabaikan dan penghitung frames tetap nol sampai timeout 8 detik.
- File yang berubah pada v2: backend/canon_edsdk_live.py.
