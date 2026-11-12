KACA.ID v0.9.76 — QRIS DINAMIS, FULLSCREEN, FILTER, WHATSAPP
=========================================================

1) QRIS / DOKU CHECKOUT
- Mode QRIS Statis tetap tersedia dengan verifikasi manual melalui PIN operator.
- Mode DOKU Checkout menambah QRIS per invoice dengan Client ID + Secret Key DOKU.
- DOKU Checkout diprioritaskan di panel transaksi; tombol tambahan menampilkan
  halaman QRIS di jendela aman KACA.ID apabila iframe dibatasi penyedia.
- PEMBAYARAN TIDAK OTOMATIS DIANGGAP BERHASIL karena QR berhasil muncul,
  pelanggan menutup halaman, atau pelanggan menekan tombol.
- Validasi pembayaran melalui GET /orders/v1/status/{invoice} DOKU, menggunakan
  signature HMAC-SHA256 dan HTTPS. Konfirmasi 'paid' hanya jika respons status
  SUCCESS serta invoice dan nominal cocok. Invoice hanya dapat dipakai satu kali
  saat memulai sesi kamera. Pengecekan pertama setelah 60 detik sesuai DOKU.
- Tidak ada kredensial merchant DOKU asli dalam ZIP; tes integration menggunakan
  MOCK ID/Secret dan respons DOKU SIMULASI, bukan transfer dana sesungguhnya.
- Pengujian pembayaran DOKU sungguhan memerlukan aktivasi QRIS merchant dan
  kredensial sandbox/production dari pemilik akun sendiri.

Pengaturan:
  Menu Pembayaran -> Konfigurasi QRIS -> set nominal -> Simpan.
  Menu Pembayaran -> QRIS Otomatis -> pilih DOKU Checkout,
  lingkungan sandbox, Client ID, Secret Key -> Simpan.
  Buka sesi baru -> transaksi -> QRIS -> scan QR DOKU.
  Jalankan simulasi pembayaran di dashboard sandbox DOKU.
  Setelah provider memberi SUCCESS, aplikasi otomatis membuka pemilihan frame.
  Ganti ke production hanya setelah uji merchant dan kredensial live siap.
  Bila mode DOKU aktif tanpa aktivasi QRIS merchant, API DOKU akan menolak transaksi.

2) FULLSCREEN CUSTOMER SLIDES 2–6
- Layout dan panel diselaraskan ke tengah viewport.
- Pengujian Chromium dengan viewport 1366x768, 1920x1080, 1100x700.
- Tombol LANJUT KE HASIL dikembalikan ke bawah daftar filter; daftar filter
  dapat di-scroll secara terpisah tanpa menggeser tombol tersebut.

3) WHATSAPP TANPA WHATSAPP CLOUD API LANGSUNG
- Tambah mode Gateway Fonnte yang menerima permintaan pesan dari backend
  tanpa membuka WhatsApp Web atau aplikasi WhatsApp.
- Menu Pengaturan Umum -> WhatsApp -> masukkan token Fonnte dan pilih
  mode Gateway Fonnte -> Simpan.
- Memerlukan perangkat WhatsApp terhubung ke penyedia, akses internet,
  dan persetujuan pelanggan. Masing-masing pelanggan/sesi dideduplikasi.
- Respons accepted berarti gateway menerima permintaan, BUKAN jaminan pesan
  telah tiba di nomor tujuan. Layanan pihak ketiga dapat memiliki ketentuan,
  biaya, pembatasan, dan risiko pembatasan akun WhatsApp.
- Alternatif resmi yang direkomendasikan untuk bisnis berkelanjutan adalah
  WhatsApp Business Platform melalui penyedia resmi, yang secara teknis tetap
  menggunakan ekosistem WhatsApp Business Platform.

4) PEMASANGAN
- Tutup KACA.ID sepenuhnya dan backup folder aplikasi.
- Patch dibuat untuk v0.9.75; salin isi patch ke folder dengan package.json.
- FULL SOURCE juga tersedia jika pengguna tidak ingin menimpa file per file.
- Jangan menyalin kredensial merchant ke file yang akan didistribusikan ke publik.

5) BATAS PENGUJIAN
- Unit test DOKU + Fonnte (simulasi): LULUS.
- HTTP integration backend DOKU + Fonnte (simulasi): LULUS.
- QRIS statis/voucher legacy: LULUS.
- Chromium fullscreen + tombol filter sticky: LULUS.
- Koneksi DOKU merchant nyata, scanning QRIS produksi, dan pengiriman WA ke
  penerima nyata: BELUM DIUJI karena tidak tersedia kredensial/akun pengguna.

Dokumentasi resmi:
DOKU: https://developers.doku.com/accept-payments/doku-checkout/integration-guide/backend-integration
DOKU Check Status: https://developers.doku.com/get-started-with-doku-api/check-status-api/non-snap
Fonnte: https://docs.fonnte.com/api-send-message/
