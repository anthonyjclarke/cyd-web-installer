# Changelog

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
