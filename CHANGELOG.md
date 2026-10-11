# Changelog

## [1.2.0] 12-10-2026

### Added

- ESP32-S3 (and other chip) support. `make_manifests.py` reads each env's
  chip from the built app image header (chip ID 0 → `ESP32`, 9 → `ESP32-S3`,
  and so on). It writes that as the manifest's `chipFamily`, which was
  hardcoded to `ESP32`, and as `chip` per board in `index.json`.
- The installer page notes that native-USB boards need no driver.

### Changed

- The README, comments and the workflow name now say "ESP32 projects", not
  "CYD projects". The repo name and `cyd-release.yml` path are unchanged, so
  callers need no edit.

### Unchanged

- ESP32 manifests are byte-identical to 1.1.0. `index.json` only gains
  `chip`.

## [1.1.0] 10-10-2026

### Added

- Optional filesystem image as a fifth manifest part, for FS option C. An env
  opts in with `custom_installer_fs = yes`. CI runs `pio run -t buildfs` for
  it, and `make_manifests.py` adds `littlefs.bin` / `spiffs.bin` at the data
  partition's offset, read from the built `partitions.bin`. It checks that
  the image is exactly the partition's size and lies past the app slots.
  `--fs-envs` lists the opted-in envs for the workflow. The manifest check
  accepts four parts, or five when the fifth is the filesystem image. The
  release also carries `*-littlefs.bin`. Specified by CYD_Family_Clock, its
  first user.

### Unchanged

- Projects that don't opt in: manifests and `index.json` are byte-identical
  to 1.0.3, and `merge_bin.py` needs no re-copy.

## [1.0.3] 10-10-2026

### Fixed

- A browser that had the page open before a release could get the previous
  release's manifest and parts from cache for up to 10 minutes, since GitHub
  Pages serves them with `max-age=600`. ESP Web Tools then showed neither
  Install nor Update. The page now loads each manifest with `?v=<version>`,
  and `make_manifests.py` adds the same query to every part path, because ESP
  Web Tools resolves parts against the manifest URL without its query.
  Reported by F1_CYD_Notifications.
- `copy-in/src/network/improv_setup.cpp` names the device after the MAC's
  last two bytes (`SplitFlap-AE8C` for `…:AE:8C`). It used the low 16 bits of
  `getEfuseMac()`, which hold the first two bytes, the vendor prefix, so
  every board from one vendor got the same suffix. Cosmetic: it only changes
  the name shown in the installer dialog. Reported by CYD_WifiScan_Display
  and CYD_Split-Flap-Clock.

## [1.0.2] 09-10-2026

### Fixed

- The installer page no longer promises **Update** or **Configure WiFi** for
  a project without Improv. `make_manifests.py` writes `"improv"` to
  `index.json` from `#define IMPROV_SETUP_ENABLED` in the config header (false
  when absent). The page then hides the Update line, and keeps the WiFi line
  only for the setup hotspot (`AP_NAME`). An `index.json` without the key is
  treated as Improv-enabled. Manifests are unchanged. Reported by
  AuroraDemo_CYD.

## [1.0.1] 09-10-2026

### Fixed

- `copy-in/lib/ImprovWiFi` starts every Improv packet with a newline. ESP Web
  Tools 10.4.0 (improv-wifi-serial-sdk 2.8.0) parses line by line and dropped
  a reply that followed serial noise on port open, so Connect intermittently
  offered **Install** instead of **Update**. Found and verified on
  CYD_Display_Test: 6/6 detections in Chrome, and RUNBOOK cases 2 and 3 pass.
  Projects that already copied the library must copy it again.

## [1.0.0] 09-10-2026

### Added

- Reusable workflow `.github/workflows/cyd-release.yml`, extracted from
  CYD_AnimatedPixelClock v1.4.0's `firmware.yml`. It keeps every guard: no
  secrets file, tag equals `v` + `FIRMWARE_VERSION`, no pre-release suffix,
  tag on `main`, and four manifest parts with no merged image.
- `tools/merge_bin.py` and `tools/make_manifests.py`. The manifests and
  `index.json` are byte-identical to the pilot's for the pilot's builds.
  `make_manifests.py` also takes `--project`, `--config`, `--page` and
  `--info`, reads `#define` as well as `constexpr` strings, and treats the
  repo URL, the upstream credit and `AP_NAME` as optional.
- Generic `installer/index.html` (ESP Web Tools 10.4.0).
- Copy-in Improv pieces: the vendored library with its parser fix, and the
  always-on `improv_setup` module with an `IMPROV_DEVICE_PREFIX` option.
- `examples/firmware.yml`, the caller workflow.
