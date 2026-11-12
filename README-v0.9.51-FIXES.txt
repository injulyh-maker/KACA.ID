KACA.ID v0.9.51 — PATCH LOG

1. Backend health: healthy KACA backend on port 8765 is adopted even if the initial PID preflight misses it; no false unhealthy state due to PID mismatch.
2. Voucher customer entry: replaces unsupported window.prompt() with an in-app dialog.
3. Voucher CSV: admin can download a template and import CSV exported from Excel. Duplicate/invalid rows are skipped and reported.
4. Payment methods: separate Voucher and QRIS enable switches. If both are off, the transaction slide is skipped and frame selection opens directly. Existing installs default to both enabled.
5. Borderless printing: do not infer lack of support only from paper-size names. All driver paper sizes remain selectable; exact driver paper selection is honored and custom size is allowed. If the driver exposes borderless only through its own Properties/DEVMODE settings, configure it there.

Important: physical printer borderless output must still be tested with the exact printer model and driver. Windows printer drivers expose capabilities differently; KACA.ID cannot guarantee true edge-to-edge output solely from a paper-size list.
