KACA.ID v0.9.39 — FRAME GOOGLE DRIVE QR

FITUR BARU
- Pengaturan Frame memiliki opsi "Sisipkan QR Google Drive ke hasil JPG untuk dicetak".
- QR placeholder dapat dipindahkan dan diubah ukurannya langsung pada pratinjau editor frame.
- Posisi dan ukuran QR disimpan per frame, terpisah dari posisi slot foto.
- QR berisi tautan folder Google Drive sesi yang sebenarnya, bukan tautan statis.
- QR dibakar ke output.jpg / Hasil_Frame.jpg sehingga menjadi bagian dari gambar cetak.
- Jika tautan Drive baru tersedia setelah render awal, hasil JPG, arsip lokal, dan ZIP lokal diperbarui.
- Jika Drive belum terhubung atau tautan belum tersedia, QR tidak dibuat secara palsu.

GOOGLE DRIVE
- File ZIP dan Session_Info.json tetap lokal dan dikecualikan dari upload Google Drive.
- Folder Photos, Live_Photos, Final_Results, dan Video_Results tetap mengikuti alur upload yang sudah ada.

FILE YANG BERUBAH
- src/app.js
- src/style.css
- src.zip (salinan app.js dan style.css disinkronkan)
- backend/camera_server.py
- tests/session_qr_test.py
- tests/google_drive_test.py
- package.json (versi 0.9.39)

CATATAN
- QR frame hanya aktif jika admin mencentang opsi di Pengaturan Frame dan tautan Google Drive sesi tersedia.
- QR yang tampil pada layar hasil sesi tetap terpisah dan tetap memakai tautan sesi yang sama.
- Canon EDSDK dan DLL tidak diubah.
- Pengujian otomatis memakai mock untuk Google Drive; belum diuji pada kamera/printer fisik.
