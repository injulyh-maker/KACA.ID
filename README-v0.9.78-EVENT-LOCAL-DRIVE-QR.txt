KACA.ID v0.9.78 — Penyimpanan Event Lokal + Drive + QR

Perubahan:
1. Sesi FOTO pada Event tersimpan terpisah di folder lokal:
   Pictures/KACA STUDIO/Events/Event_<ID_EVENT>/Sesi_<TANGGAL>_<NOMOR>/
   dengan Photos, Live_Photos, Final_Results, Session_Info.json, ZIP hasil.
   Mode umum tidak berubah, tetap di Pictures/KACA STUDIO/Sesi_... .
2. Di Google Drive, folder event tersusun sebagai:
   KACA STUDIO/Events/Event_<ID_EVENT>/Sesi_.../
   Per sesi dibuatkan link tersendiri dan QR lokal sendiri, untuk privasi antar tamu.
3. QR di slide hasil dan detail arsip dapat dipindai untuk membuka folder sesi.
   QR baru akan tersedia setelah pembuatan folder Drive berhasil; upload file dapat berjalan belakangan.
4. VIDEO mandiri pada Event disimpan di Events/Event_<ID_EVENT>/Video_Results/.
   Video diunggah ke Events/Event_<ID_EVENT>/Video_<ID_VIDEO>/Video_Results/.
   Setelah upload siap, preview hasil video akan menampilkan QR yang menuju folder video tersebut.
5. Manajemen Event menyediakan tombol Lihat Hasil Event Aktif.

Panduan patch:
- Backup folder aplikasi, termasuk seluruh data/settings, sebelum menimpa patch.
- Tutup frontend dan backend KACA.ID.
- Salin isi folder patch ke folder utama aplikasi yang berisi package.json.
- Jalankan kembali run-kaca-id.bat.
- Uji satu sesi PHOTO event dengan Google Drive terhubung, lalu scan QR dan pastikan hasil di Drive.
- Uji satu sesi VIDEO mandiri pada Event jika fitur VIDEO digunakan.

Catatan penting:
- Tidak ada migrasi otomatis untuk arsip event dari versi sebelum 0.9.78. Arsip lama tidak dipindahkan.
- Event dan sesi umum tetap menggunakan satu koneksi Google Drive OAuth yang sama.
- Google Drive harus terhubung dan izin berbagi folder sesi harus benar agar QR dapat diakses tamu.
- Pengujian otomatis menggunakan tiruan respons API Drive; akun Drive sungguhan perlu diuji di komputer booth.
