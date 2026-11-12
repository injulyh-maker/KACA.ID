KACA.ID v0.9.14 - Bundled Canon EDSDK package

Active x64 runtime:
  EDSDK.dll

Full original SDK package:
  SDK_Package/EDSDK/

The full package is preserved without changing its contents. The supplied
EdsImage.dll under SDK_Package/EDSDK/Dll is x86 (32-bit), while the KACA.ID
backend is x64. Do not copy that x86 file next to the active EDSDK.dll.
Use an x64 EdsImage.dll from the matching official Canon SDK if a future
image-processing integration requires it.

The current adapter uses the EDSDK C API through ctypes for camera discovery.
The bundled CPython .pyd bindings are retained for future native integration;
they are not loaded by the current discovery adapter.
