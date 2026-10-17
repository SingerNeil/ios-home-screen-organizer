# Reverse-engineering and clean-room record

## Target observations

- Target: a locally supplied Unjiggle 1.1.3 (8) arm64 app bundle.
- REA 6.5.0 Mach-O evidence:
  `ev_01f49d8902a320eabde5c8fc275f47095359c50510e97fc15e5b4a50ad8771b6`.
- Visible product surfaces: Connect, Diagnosis, Swipe Tax, Mirror, Obituary,
  Transform, and app inventory.
- A paired iOS device exposes icon-state reads and writes through the public
  `com.apple.springboardservices` protocol implemented by pymobiledevice3.

These are observations, not copied implementation.

## Independent design choices

- Native SwiftUI UI and a Python subprocess with a one-shot JSON protocol.
- Transparent local scoring/category rules and deterministic prose.
- Four original sorting presets; no claim of byte-for-byte or algorithmic
  equivalence with the inspected product.
- Preview plans are bound to the device and exact source-layout hash.
- Apply and restore each create recovery data before writing.
- No account, licensing, updater, analytics, or cloud-AI subsystem.

The original application is not a build input and remains unchanged. No
proprietary source, resource, or executable is present in this repository.

## Validation boundary

Unit tests cover deterministic analysis, non-mutating previews, hashes, and
backup round trips. Packaged verification checks the native signature and runs
four backend flows from inside the app. Live reads and writes still require a
physically connected, paired iPhone or iPad and cannot be claimed as verified
without one.
