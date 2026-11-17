# KACA.ID Android USB/PTP validation matrix - v0.9.93 beta

| Physical test | Expected | Result |
|---|---|---|
| Android USB Host + DSLR OTG | USB/PTP camera listed | Not tested |
| USB access denied | No device connection | Not tested |
| USB access granted | Probe returns supported operations | Not tested |
| PTP DSLR supports 0x100E | New JPEG saved and composited | Not tested |
| DSLR vendor-only PTP shutter | Explicit unsupported-operation error | Not tested |
| DSLR RAW-only | Explicit JPEG/RAW+JPEG recommendation | Not tested |
| Disconnect camera mid-capture | Error surfaced, UI remains usable | Not tested |
| 4R/2R print via Android PrintService | Print dialog opens | Not tested |
| USB printer without driver | Detected, no false print claim | Not tested |
| Rotate tablet and open long settings | Scroll reaches final control | Not tested |

Important: PTP, printer media support, firmware modes, and print services vary by model. This source update does not establish compatibility with every DSLR or photo printer.
