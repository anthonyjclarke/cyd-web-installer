# Changelog

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
