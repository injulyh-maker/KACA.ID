KACA.ID — Canon EDSDK Process Isolation Patch v2

Tujuan:
- Melaporkan tahap startup worker secara bertahap.
- Membedakan macet saat worker boot/import/controller/native_start.
- Menampilkan PID, exitcode, dan tahap terakhir jika timeout.
- Tidak mengubah camera_server.py, canon_edsdk_runtime.py, atau jalur webcam.

PENTING:
Patch v2 mengasumsikan patch v1 sudah memasang canon_edsdk_native.py.
Jangan hapus file tersebut. File ini adalah salinan native controller asli.

Cara memasang:
1. Ekstrak ZIP.
2. Buka PowerShell pada folder proyek KACA.ID (folder yang berisi backend).
3. Jalankan:
   powershell -ExecutionPolicy Bypass -File .\APPLY-CANON-PROCESS-V2.ps1
4. Jalankan aplikasi seperti biasa.
5. Pilih Canon dan kirimkan log error lengkap, terutama bagian:
   - Tahap terakhir
   - PID
   - exitcode
   - alive

Jika tahap terakhir `native_start`, worker telah berhasil boot, import modul, dan membuat controller; hambatan berada di dalam `NativeCanonLiveView.start()` atau pemanggilan native EDSDK di dalamnya.

Backup otomatis dibuat untuk dua file yang diganti.
