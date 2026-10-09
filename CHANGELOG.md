# Changelog

## [1.0.3] 10-10-2026

### Fixed

- A browser that had the page open before a release could get the previous
  release's manifest and parts from cache for up to 10 minutes, since GitHub
  Pages serves them with `max-age=600`. ESP Web Tools then showed neither
  Install nor Update. The page now loads each manifest with `?v=<version>`,
  and `make_manifests.py` adds the same query to every part path, because ESP
  Web Tools resolves parts against the manifest URL without its query.
  Reported by F1_CYD_Notifications.

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
