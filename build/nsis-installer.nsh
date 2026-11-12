!include "LogicLib.nsh"

!macro customInstall
  ; This installer is per-machine and elevated by electron-builder.
  ; The Microsoft installer is embedded as a resource, so this works offline.
  ; Always run the bundled current VC++ runtime: checking only "Installed=1"
  ; is not enough, because an older 2015 runtime may be present.
  IfFileExists "$INSTDIR\resources\vc_redist.x64.exe" 0 vc_runtime_missing
    DetailPrint "Memastikan Microsoft Visual C++ Runtime x64 terbaru tersedia..."
    ExecWait '"$INSTDIR\resources\vc_redist.x64.exe" /install /quiet /norestart' $0
    ${If} $0 == 0
      DetailPrint "Microsoft VC++ Runtime selesai dipasang atau diperbarui."
    ${ElseIf} $0 == 1638
      DetailPrint "Microsoft VC++ Runtime sama atau lebih baru sudah terpasang."
    ${ElseIf} $0 == 3010
      MessageBox MB_ICONINFORMATION|MB_OK "VC++ Runtime berhasil dipasang, tetapi Windows perlu direstart sebelum memakai KACA.ID."
    ${Else}
      MessageBox MB_ICONSTOP|MB_OK "Runtime Microsoft Visual C++ gagal dipasang (kode $0). Pemasangan KACA.ID dihentikan agar aplikasi tidak rusak."
      Abort
    ${EndIf}
    Goto vc_runtime_done
  vc_runtime_missing:
    MessageBox MB_ICONSTOP|MB_OK "VC++ Redistributable tidak ditemukan di dalam paket installer. Jangan gunakan installer ini; hubungi penerbit."
    Abort
  vc_runtime_done:
    IfFileExists "$INSTDIR\resources\python\python.exe" 0 python_runtime_missing
      DetailPrint "Python portable 3.12 beserta paket kamera terbundel."
      Goto runtime_all_ready
  python_runtime_missing:
    MessageBox MB_ICONSTOP|MB_OK "Python portable tidak ditemukan di dalam paket installer. Pemasangan dibatalkan."
    Abort
  runtime_all_ready:
!macroend
