KACA.ID v0.9.52 — VOUCHER SESSION INITIALIZATION & BULK MANAGEMENT

Perbaikan: 
1. Mencegah pelanggan menekan metode transaksi saat renderCapture masih menunggu daftar frame/kamera. Tombol Voucher dan QRIS tetap disabled sampai seluruh deklarasi state/handler sesi siap, sehingga setFlowStep tidak membaca binding `take` sebelum inisialisasi (Temporal Dead Zone).
2. Menu Voucher memiliki checkbox per kode dan Pilih Semua. Admin dapat menghapus voucher terpilih, semua voucher kedaluwarsa, atau seluruh voucher. Penghapusan dilakukan di backend dengan lock dan penyimpanan JSON atomik.
3. Penghapusan voucher kedaluwarsa memakai tanggal expires_at secara langsung, termasuk voucher yang sebelumnya dinonaktifkan.

Catatan: uji kamera fisik dan alur transaksi pada Windows tetap perlu dilakukan di perangkat booth.
