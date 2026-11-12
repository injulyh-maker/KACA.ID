# KACA.ID 0.9.88 — Icon & Cloud Branding (patch)

Logo dasar: gambar yang diserahkan pengguna (`build/logo-source-original.png`).
Mark hitam asli dipertahankan, diletakkan pada kotak putih bersudut bulat
agar terlihat di taskbar Windows terang atau gelap.

## Ikon sudah dihubungkan
- `build/icon.ico` → Electron Builder EXE, shortcut Desktop/Start Menu, NSIS installer/uninstaller.
- `build/icon.png` → `BrowserWindow` Electron (aplikasi utama dan checkout QRIS DOKU).
- `src/assets/kaca-loading-brand.png` → logo loading pertama aplikasi.
- `cloud_control/web/favicon.ico`, `favicon-32.png` → favicon browser.
- `cloud_control/web/logo-kaca-192.png` → logo di sidebar dan login KACA.ID Cloud Control.
- `cloud_control/web/apple-touch-icon.png` → icon web di perangkat mobile.
- `cloud_control/server.py` → melayani `/favicon.ico` juga.
- `cloud_control/activate.html` → ikon jendela aktivasi lokal.

## Cara pasang pada source KACA.ID v0.9.88
1. Backup source dan data KACA.ID.
2. Tutup aplikasi Electron dan hentikan server Cloud Control jika masih berjalan.
3. Ekstrak ZIP patch; salin *isi* folder `KACA-ID-v0.9.88-PATCH-LOGO-ICON` ke folder source yang berisi `package.json`.
4. Pilih Replace untuk file yang sudah ada. Jangan menyalin folder `runtime`, `media`, atau data pelanggan dari komputer lain.
5. Jalankan kembali server Cloud Control dengan perintah lama, kemudian reload browser memakai Ctrl+F5.
6. Icon Taskbar/Start Menu/installer dari EXE yang lama tidak berubah hanya dengan menyalin PNG/ICO: REBUILD installer di Windows/GitHub Actions:
   - `build-windows-installer.bat`, atau
   - Github Actions -> KACA.ID - Windows Installer -> Run workflow.
7. Installer hasil build harus berisi Python portable, Microsoft Visual C++ runtime, dan icon baru. Tidak diperlukan Python manual pada komputer pengguna.

## Pengujian yang telah dilakukan
- ICO berisi ukuran 16,24,32,48,64,128,256 piksel.
- Parser Electron main.js dan server.py lulus syntax check.
- Electron Builder dan NSIS diarahkan ke icon.ico.
- Cloud Control login/sidebar menampilkan logo PNG (uji Chromium dengan aset lokal).
- Tes build/icon dan aset: `python build/check-brand-assets.py`.
- Tes runtime packaging: `python build/test_packaging_configuration.py`.

## Belum diuji
EXE final pada Windows bersih serta instalasi VC++/Python otomatis membutuhkan
build di runner Windows dan pengujian Windows fisik. ZIP ini berisi source
serta builder, **bukan installer .exe yang sudah dikompilasi**.

## Catatan
Nomor versi aplikasi tetap 0.9.88 (branding-only), untuk menghindari konflik
protokol backend serta lisensi. Alur foto, video, kamera, QR, Cloud, dan data
pelanggan tidak diubah.
