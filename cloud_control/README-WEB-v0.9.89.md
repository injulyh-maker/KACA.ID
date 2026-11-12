# KACA.ID Cloud Control v0.9.89 — Pengembangan Web Lokal

**Basis desktop:** KACA.ID v0.9.88. Update ini hanya mengubah `cloud_control/server.py`, `cloud_control/web/index.html`, dan file pengujian/dokumentasi. **Tidak memerlukan GitHub atau build installer Windows.** Server Cloud Control tetap lokal sampai Anda sendiri men-deploy-nya.

## Peningkatan yang tersedia

1. Dashboard menampilkan grafik jumlah sesi harian (7, 30, atau 90 hari), filter booth, dan ringkasan pembayaran terverifikasi vs estimasi.
2. Hasil & Sesi menampilkan 10 baris per halaman, filter booth, PHOTO/VIDEO, tanggal mulai/akhir, serta ekspor CSV yang dapat dibuka Excel. Ekspor dibatasi maksimal 10.000 baris per permintaan.
3. Super Admin bisa melihat pemilik dan status seluruh lisensi serta menangguhkan/mengaktifkan kembali akses Cloud. Setiap perubahan dicatat pada audit.
4. Catatan audit dapat dibaca dari panel Super Admin. Akun pengguna biasa tidak dapat membaca audit atau mengubah lisensi.
5. Endpoint pemeriksaan server `/api/health`, header keamanan dasar, dan tanggal laporan default **WITA (UTC+8)**, dapat disesuaikan dengan `KACA_CLOUD_REPORT_TZ_MINUTES`.
6. Semua fitur sebelumnya tetap ada: registrasi/login, lisensi Ed25519 untuk offline, dua atau lebih booth per akun, pemantauan sesi, voucher, pengaturan remote, dan izin operator untuk preview remote.

**Batasan penting:** ini masih **tahap pengembangan lokal**, belum siap langsung diekspos ke internet publik. Belum ada MFA, verifikasi email, sistem recovery akun, rate-limit terdistribusi, backup terotomasi teruji, database produksi PostgreSQL, TLS reverse proxy, atau audit penetrasi. Remote tetap hanya dapat mengendalikan jendela aplikasi dengan izin operator, bukan seluruh Windows.

## Memperbarui web yang sudah tampil di `127.0.0.1:8086`

1. **Hentikan server web** dengan `Ctrl+C` di terminal server Cloud Control (tidak perlu menutup aplikasi booth yang sedang mengambil foto).
2. **Backup data Cloud** sebelum mengganti source: jika memakai environment `KACA_CLOUD_DATA_DIR`, backup seluruh folder tersebut; jika tidak, backup `cloud_control/data` termasuk **database `cloud.sqlite3` dan private key `ed25519-private.pem`**. Jangan menyimpan private key di repository atau mengirimkannya kepada orang lain.
3. Ekstrak ZIP `KACA-ID-v0.9.89-CLOUD-WEB-UPDATE.zip`, lalu salin isi folder paket ke **folder utama source v0.9.88**, tempat `package.json` berada. Ganti `cloud_control/server.py` dan `cloud_control/web/index.html`. **Jangan menimpa atau menghapus folder `cloud_control/data`.**
4. Dari PowerShell di folder utama source, jalankan:

   ```powershell
   .\cloud-env\Scripts\python.exe -m pip install -r cloud_control\requirements.txt
   .\cloud-env\Scripts\python.exe -m uvicorn cloud_control.server:app --host 127.0.0.1 --port 8086
   ```

   Jika Python environment Anda bernama lain, gunakan interpreter yang sama dengan yang selama ini menjalankan web.
5. Buka `http://127.0.0.1:8086/api/health` untuk melihat status server. Kemudian buka `http://127.0.0.1:8086` dan tekan `Ctrl+F5` agar browser memuat kode web yang baru.
6. Login menggunakan akun Super Admin yang **sudah Anda miliki**. **Tidak perlu membuat akun admin atau menerbitkan ulang lisensi.**

## Pengujian sebelum melanjutkan ke GitHub

- Masuk sebagai Super Admin, lalu buka **Dashboard** → ubah grafik 7 / 30 / 90 hari.
- Buka **Hasil & Sesi**, pilih booth, tanggal, PHOTO/VIDEO, lalu uji tombol Berikutnya dan Unduh CSV.
- Di **Super Admin**, periksa status lisensi dan audit. Uji penangguhan **hanya menggunakan booth percobaan**, bukan booth pelanggan yang sedang digunakan.
- Masuk dengan akun pengguna biasa, pastikan **Super Admin** tidak terlihat dan API admin menolak akses.
- Aktifkan booth percobaan melalui Cloud Control desktop; gunakan **Sinkronkan Sekarang** untuk memunculkan data sesi. Saat internet putus, sesi booth harus tetap bekerja secara lokal.

## Keterangan lisensi

Penangguhan lisensi menghentikan autentikasi agen **ketika ia berikutnya terhubung ke Cloud**. Aplikasi booth yang offline dan masih menyimpan lisensi digital valid **tidak dapat langsung dihentikan dari web**. Untuk kebijakan pencabutan offline, diperlukan periode lisensi pendek atau mekanisme pemberian ulang lisensi dengan periode tenggang yang disepakati.

## Status pengujian developer

- Unit dan API menggunakan basis data sementara: login, 2 akun, 3 booth, 2 lisensi satu akun, isolasi akses, grafik tren, pagination dan filter, export CSV, admin suspend/restore, audit — **lulus**.
- Chromium dengan API simulasi: dashboard, grafik, pagination, filter, ekspor, daftar lisensi admin dan audit — **lulus tanpa exception JavaScript**.
- Pengujian akses `localhost` browser di lingkungan developer diblokir kebijakan alat. Halaman UI diuji secara terpisah dari API. Server langsung diuji melalui FastAPI TestClient / HTTP.
- Belum diuji melalui akun dan booth Windows produksi milik Anda, domain internet publik, atau alur remote dengan perangkat fisik.

**Versioning:** Desktop/Electron tetap `0.9.88`; web API melaporkan `0.9.89-web` untuk memudahkan identifikasi. Tidak ada perombakan skema database sehingga data lama dipertahankan.
