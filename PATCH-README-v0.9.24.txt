KACA.ID v0.9.24 — KEYBOARD, STORAGE PATH, DUPLICATE SLOTS, IMAGE BACKGROUND

- Virtual keypad for numeric PIN and WhatsApp number fields.
- Runtime-configurable local session archive root, persisted in Electron settings and passed to backend at startup.
- Duplicate visual slots map to photo_index; JPG, filter preview, and Live Photo rendering reuse the selected source photo.
- Dashboard background supports custom image/video, clear custom background, and restore built-in video.
- Canon EDSDK files are byte-for-byte unchanged from v0.9.21 baseline.
- Windows NSIS build configuration and build-windows-installer.bat included.

Run verify-kaca-id.bat for static checks and the included smoke test. Windows installer build requires Windows and npm registry access.
