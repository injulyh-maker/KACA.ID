KACA.ID - CANON LIVE VIEW PATCH (v0.9.18)
==========================================

ISI PATCH
---------
backend/canon_edsdk_native.py
backend/canon_edsdk_worker.py

PERUBAHAN
---------
1. Mengubah urutan inisialisasi Live View:
   - Membaca EVF Output Device.
   - Mengaktifkan output PC sambil mempertahankan flag output kamera.
   - Mengaktifkan EVF Mode setelah output PC diatur.
   - Memproses event awal kamera.
2. Menambahkan pelaporan tahap native EDSDK secara rinci. Jika startup macet,
   log akan menunjukkan operasi terakhir, bukan hanya "native_start".

TEMUAN DARI DSLR BOOTH
----------------------
Paket DSLR Booth berisi EDSDK.dll 64-bit, Canon.Eos.Framework.dll, dan
CameraControl.Devices.dll. Dua framework .NET tersebut bukan pengganti
langsung modul Python KACA.ID. Patch ini menerapkan perbaikan alur EVF dan
diagnostik tanpa menyalin binary/framework proprietary DSLR Booth.

CARA MEMASANG
-------------
1. Tutup KACA.ID, DSLR Booth, EOS Utility, dan aplikasi kamera lain.
2. Buat salinan cadangan folder proyek KACA-ID-v0.9.18.
3. Ekstrak isi ZIP patch ke folder utama proyek KACA-ID-v0.9.18.
   Izinkan Windows mengganti dua file di dalam folder backend.
4. Jalankan KACA.ID seperti biasa.
5. Sambungkan kamera, pilih Canon EDSDK, lalu buka preview.

CARA MEMBACA LOG
----------------
- Jika berhenti pada open_session: periksa pembukaan sesi/kunci kamera.
- Jika berhenti pada read_evf_output atau set_evf_output_pc: periksa akses
  properti EVF kamera.
- Jika berhenti pada set_evf_mode atau pump_initial_events: periksa aktivasi
  EVF dan event kamera.
- Jika mencapai start_evf_frame_loop tetapi tidak ada gambar: fokus berikutnya
  adalah EdsDownloadEvfImage, stream JPEG, dan pengiriman frame ke UI.

CATATAN
-------
Patch ini sudah diperiksa sintaks Python-nya, tetapi belum dapat diuji pada
kamera fisik dari lingkungan ini. Keberhasilan preview tetap perlu diuji
dengan model kamera dan komputer Anda. Jangan jalankan DSLR Booth/EOS Utility
bersamaan saat menguji KACA.ID karena kamera dapat dikunci aplikasi lain.
