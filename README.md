# cyd-web-installer

Shared ESP Web Tools installer tooling for ESP32 CYD (Cheap Yellow Display)
projects. A project that adopts it gets a GitHub Pages page where anyone with
Chrome or Edge picks their board, clicks **Install**, and ends up on WiFi. They
don't need PlatformIO, esptool or drivers. Boards that already run the firmware
are offered **Update**, which keeps their settings.

The pilot, and the reference for every rule below, is
[CYD_AnimatedPixelClock](https://github.com/anthonyjclarke/CYD_AnimatedPixelClock)
([live installer](https://anthonyjclarke.github.io/CYD_AnimatedPixelClock/)).
Its `docs/WEB_INSTALLER_PLAN.md` has the design and the hardware test results.
The hub at [anthonyjclarke.github.io](https://anthonyjclarke.github.io/) lists
every project that has an installer.

---

## Contents

| Path                                 | Role                                  |
|:-------------------------------------|:--------------------------------------|
| `.github/workflows/cyd-release.yml`  | Reusable build, release and Pages job |
| `tools/merge_bin.py`                 | PlatformIO post-script; copy in       |
| `tools/make_manifests.py`            | Builds `_site/` from the builds       |
| `installer/index.html`               | Generic page driven by `index.json`   |
| `copy-in/lib/ImprovWiFi/`            | Improv library, parser fix; copy in   |
| `copy-in/src/network/improv_setup.*` | Always-on Improv module; copy in      |
| `examples/firmware.yml`              | The caller workflow                   |

The workflow fetches `make_manifests.py` and the page from this repo at
`tools-ref`, so a project copies only `merge_bin.py` and, if it needs them,
the Improv pieces (see [`copy-in/README.md`](copy-in/README.md)).

---

## Per-project contract

| Requirement                               | Why                                    |
|:------------------------------------------|:---------------------------------------|
| `FIRMWARE_VERSION` + `PROJECT_NAME`       | Manifest version, same-firmware check  |
| Both in one header, as string             | `constexpr … = "x"` or `#define X "x"` |
| `PROJECT_NAME` never changes              | A rename turns Update into Install     |
| Builds with no `secrets.h`                | CI can build a shippable image         |
| Pinned `platform =`                       | Reproducible release builds            |
| One `[env:]` per board                    | One manifest and button per board      |
| `custom_installer_label` per env          | Board picker text, no HTML edits       |
| `custom_installer_hint` (optional)        | One line under the label               |
| `extra_scripts = post:tools/merge_bin.py` | Writes `flash_parts.json`              |
| Standard 4 MB dual-OTA partitions         | Frozen once released; one recipe       |
| Improv-Serial, always on (advised)        | WiFi in the dialog; offers Update      |
| `main` for releases, `dev` for work       | Tags must be on `main`                 |

`index.json` also picks up these optional `config.h` strings when present:
`PROJECT_REPO_URL` (otherwise the GitHub repo URL), `UPSTREAM_PROJECT`,
`UPSTREAM_AUTHOR` and `UPSTREAM_REPO_URL` (a "Based on" credit), and `AP_NAME`
(the setup hotspot, shown as a WiFi alternative).

An env without `custom_installer_label` is still built in CI but left out of
the installer.

---

## Caller workflow

Copy [`examples/firmware.yml`](examples/firmware.yml) to
`.github/workflows/firmware.yml`:

```yaml
name: Firmware
on:
  push: { branches: [dev, main], tags: ["v*"] }
  pull_request:
  workflow_dispatch:
jobs:
  firmware:
    uses: anthonyjclarke/cyd-web-installer/.github/workflows/cyd-release.yml@main
    permissions: { contents: write, pages: write, id-token: write }
```

The `permissions` line is required. A called workflow gets no more than its
caller grants, and the publish job needs all three. The build job itself runs
with `contents: read`.

Inputs, all optional:

| Input           | Default             | Use                                 |
|:----------------|:--------------------|:------------------------------------|
| `config-header` | `include/config.h`  | Where the version and name live     |
| `envs`          | every `[env:]`      | Space-separated subset to build     |
| `secret-files`  | `include/secrets.h` | Paths that must not be in the tree  |
| `tools-ref`     | `main`              | Ref of this repo for tools and page |

To pin, replace `@main` with a commit SHA and pass the same SHA as
`tools-ref`, so the workflow and its tools always match.

---

## What the workflow does

Every push and pull request builds every board and keeps a `site-preview`
artifact for 7 days. That artifact is never deployed. A `v*` tag also stages
the release images and deploys Pages. The guards are these:

1. It fails if a file in `secret-files` exists. Local builds compile in your
   WiFi credentials, so release images come only from CI.
2. The tag must equal `v` + `FIRMWARE_VERSION`.
3. The version must have no pre-release suffix (no `-dev`).
4. The tagged commit must be on `main`.
5. Each manifest lists exactly four parts: `bootloader.bin`,
   `partitions.bin`, `boot_app0.bin` and the app. It never lists
   `firmware-merged.bin`, because `merge_bin` fills NVS with `0xFF` and an
   "Update" would wipe WiFi and settings. Both `make_manifests.py` and a
   workflow step check this.

The release carries `*-firmware.bin` (the app, for web OTA),
`*-merged.bin` (a clean install at `0x0` that erases NVS) and
`SHA256SUMS.txt`.

---

## One-time setup per repo

1. **Settings → Pages → Source:** GitHub Actions.
2. **Settings → Environments → `github-pages` → Deployment branches and
   tags:** add a tag rule `v*`. The default allows only `main`, so a tag
   release builds and is then refused at deploy.
3. Add the repo name to `projects.json` in
   [anthonyjclarke.github.io](https://github.com/anthonyjclarke/anthonyjclarke.github.io).

---

## Try the site locally

After `pio run` has built every env:

```bash
python3 ../cyd-web-installer/tools/make_manifests.py --out _site
```

```bash
python3 -m http.server -d _site 8000
```

Web Serial works on `http://localhost`. Never publish this local site: it was
built with your `secrets.h`.

---

## Lessons from the pilot

- A merged image wipes NVS, so manifests use separate parts. The merged
  image is a clean-install download only.
- `boot_app0.bin` must be a part. A board last updated by web OTA runs
  from `app1`, and writing only the app at `0x10000` leaves it there.
- ESP Web Tools offers **Update** (no erase) only when Improv's firmware
  name equals the manifest `name`, and Improv must answer within 1.5 s of
  Connect. So Improv listens in `loop()`, not only on a fresh device.
- jnthas *Improv WiFi Library* 0.0.2–0.0.4 drops every second request. Use
  the vendored copy in `copy-in/lib/ImprovWiFi`.
- Chrome holds the serial port while the installer dialog is open. Close
  it before opening a serial monitor.
- ESP Web Tools caches the manifest per button, so the page builds a fresh
  button when the board changes.
- A partition-table change after release needs an erase, and the release
  notes must say so.
