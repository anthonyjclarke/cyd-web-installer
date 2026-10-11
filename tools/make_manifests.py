#!/usr/bin/env python3
"""Assemble the web installer site from finished PlatformIO builds.

Run from the project root after `pio run` has built every env:

    python3 <cyd-web-installer>/tools/make_manifests.py [--out _site]

For each env in platformio.ini that has `custom_installer_label`, it copies
the flash parts listed in .pio/build/<env>/flash_parts.json (written by
tools/merge_bin.py) and writes an ESP Web Tools manifest. It also writes
index.json, which the installer page and the hub read, and copies the
generic installer page (installer/index.html in this repo).

The manifest lists the parts separately and never the merged image. The
merged image fills the NVS partition with 0xFF, so an "Update" through it
would erase settings and WiFi. The manifest `name` is PROJECT_NAME, the same
string Improv reports. That match is what makes ESP Web Tools offer "Update"
rather than "Install".

`--info` prints `project=` and `version=` lines and builds nothing; CI uses
it for the tag checks, so the version is parsed in one place only.

An env with `custom_installer_fs = yes` also ships its filesystem image
(`pio run -t buildfs` output) as a fifth part, at the data partition's offset
read from the built partitions.bin. Install and Update both write it, so that
filesystem may hold shipped assets only, never settings. `--fs-envs` lists
those envs for CI's buildfs step.

Release checks (tag vs version, no -dev) belong to CI, not here, so the site
can be built and tried locally from a -dev build.
"""

import argparse
import configparser
import json
import os
import re
import shutil
import struct
import sys
from pathlib import Path
from urllib.parse import quote

TOOLS_ROOT = Path(__file__).resolve().parent.parent
# The first three parts, in flash order. The fourth is the app image.
LOADER_PARTS = ["bootloader.bin", "partitions.bin", "boot_app0.bin"]


def config_value(text, name):
    """`constexpr ... NAME = "x"` or `#define NAME "x"`; None if absent."""
    m = (re.search(r'\b%s\s*=\s*"([^"]*)"' % name, text)
         or re.search(r'#define\s+%s\s+"([^"]*)"' % name, text))
    return m.group(1) if m else None


def improv_enabled(text):
    """True when the header has `#define IMPROV_SETUP_ENABLED 1`."""
    m = re.search(r'^\s*#define\s+IMPROV_SETUP_ENABLED\s+(\d+)', text, re.M)
    return bool(m and int(m.group(1)))


def config_string(text, name, config_h):
    value = config_value(text, name)
    if value is None:
        sys.exit("error: %s not found in %s" % (name, config_h))
    return value


def installer_envs(root):
    """Envs with an installer label, and {env: filesystem} for those that
    opt in to shipping their filesystem image."""
    ini = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";",))
    ini.read(root / "platformio.ini", encoding="utf-8")
    envs, fs = [], {}
    for section in ini.sections():
        if section.startswith("env:") and ini.has_option(section, "custom_installer_label"):
            env = section[len("env:"):]
            envs.append({
                "env": env,
                "label": ini.get(section, "custom_installer_label"),
                "hint": ini.get(section, "custom_installer_hint", fallback=""),
            })
            if ini.get(section, "custom_installer_fs", fallback="no").strip().lower() in ("yes", "true", "1"):
                default = ini.get("env", "board_build.filesystem", fallback="spiffs") \
                    if ini.has_section("env") else "spiffs"
                fs[env] = ini.get(section, "board_build.filesystem", fallback=default).strip()
    return envs, fs


def data_partition(partitions_bin):
    """(offset, size) of the SPIFFS/LittleFS data partition, and the end of the
    last app partition, from a built partitions.bin. Entries are 32 bytes:
    magic AA 50, type, subtype, offset u32 LE, size u32 LE, label, flags."""
    raw = Path(partitions_bin).read_bytes()
    data, app_end = None, 0
    for i in range(0, len(raw) - 31, 32):
        if raw[i:i + 2] != b"\xaa\x50":
            break  # MD5 entry or erased flash ends the table
        ptype, subtype = raw[i + 2], raw[i + 3]
        offset, size = struct.unpack_from("<II", raw, i + 4)
        if ptype == 0x00:
            app_end = max(app_end, offset + size)
        elif ptype == 0x01 and subtype in (0x82, 0x83) and data is None:
            data = (offset, size)  # 0x82 spiffs (LittleFS uses it too), 0x83 littlefs
    return data, app_end


# chip_id in the ESP image header (bytes 12-13) -> ESP Web Tools chipFamily,
# which must equal the name esptool-js reports for the connected chip.
CHIP_FAMILIES = {0: "ESP32", 2: "ESP32-S2", 5: "ESP32-C3", 9: "ESP32-S3",
                 12: "ESP32-C2", 13: "ESP32-C6", 16: "ESP32-H2"}


def chip_family(app_bin):
    """ESP Web Tools chipFamily of a built app image, from its header."""
    head = Path(app_bin).read_bytes()[:16]
    if len(head) < 16 or head[0] != 0xE9:
        sys.exit("error: %s is not an ESP app image" % app_bin)
    chip_id = int.from_bytes(head[12:14], "little")
    if chip_id not in CHIP_FAMILIES:
        sys.exit("error: %s: unknown chip id %d" % (app_bin, chip_id))
    return CHIP_FAMILIES[chip_id]


def check_parts(env, parts):
    """Four separate parts, never the merged image (it wipes NVS)."""
    names = [Path(p["path"]).name for p in parts]
    if any("merged" in n for n in names):
        sys.exit("error: %s: a merged image is listed as a part - it erases NVS" % env)
    if len(names) != 4 or names[:3] != LOADER_PARTS:
        sys.exit("error: %s: expected %s + app, got %s"
                 % (env, ", ".join(LOADER_PARTS), ", ".join(names)))


def repo_url():
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY")
    return "%s/%s" % (server, repo) if repo else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="_site", help="output directory (default _site)")
    ap.add_argument("--project", default=".", help="PlatformIO project root (default .)")
    ap.add_argument("--config", default="include/config.h",
                    help="header holding PROJECT_NAME and FIRMWARE_VERSION")
    ap.add_argument("--page", default=str(TOOLS_ROOT / "installer" / "index.html"),
                    help="installer page to publish (default: this repo's generic page)")
    ap.add_argument("--info", action="store_true",
                    help="print project= and version= lines, then exit")
    ap.add_argument("--fs-envs", action="store_true",
                    help="print the envs with custom_installer_fs = yes, then exit")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    out = root / args.out
    config_h = root / args.config

    cfg = config_h.read_text(encoding="utf-8")
    project = config_string(cfg, "PROJECT_NAME", config_h)
    version = config_string(cfg, "FIRMWARE_VERSION", config_h)
    if args.info:
        print("project=%s\nversion=%s" % (project, version))
        return

    envs, fs_envs = installer_envs(root)
    if args.fs_envs:
        for env in fs_envs:
            print(env)
        return
    if not envs:
        sys.exit("error: no env in platformio.ini has custom_installer_label")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    boards = []
    for b in envs:
        build = root / ".pio" / "build" / b["env"]
        parts_file = build / "flash_parts.json"
        if not parts_file.exists():
            sys.exit("error: %s missing - build %s first (is tools/merge_bin.py in "
                     "extra_scripts?)" % (parts_file, b["env"]))
        dest = out / "firmware" / b["env"]
        dest.mkdir(parents=True)

        built = json.loads(parts_file.read_text())
        check_parts(b["env"], built)
        chip = chip_family(built[-1]["path"])
        parts = []
        for part in built:
            src = Path(part["path"])
            shutil.copy2(src, dest / src.name)
            # ?v= makes each release a new URL. Pages serves with max-age=600,
            # so a browser could otherwise flash a cached part from the last
            # release. ESP Web Tools resolves parts against the manifest URL,
            # which doesn't carry its own query string over.
            parts.append({"path": "firmware/%s/%s?v=%s" % (b["env"], src.name, quote(version)),
                          "offset": part["offset"]})

        if b["env"] in fs_envs:
            filesystem = fs_envs[b["env"]]
            image = build / ("%s.bin" % filesystem)
            if not image.exists():
                sys.exit("error: %s missing - run pio run -e %s -t buildfs" % (image, b["env"]))
            partition, app_end = data_partition(build / "partitions.bin")
            if partition is None:
                sys.exit("error: %s: no spiffs/littlefs data partition in partitions.bin" % b["env"])
            offset, size = partition
            if offset < app_end:
                sys.exit("error: %s: data partition 0x%x overlaps the app slots" % (b["env"], offset))
            if image.stat().st_size != size:
                sys.exit("error: %s is %d bytes, but its partition is %d"
                         % (image, image.stat().st_size, size))
            shutil.copy2(image, dest / image.name)
            parts.append({"path": "firmware/%s/%s?v=%s" % (b["env"], image.name, quote(version)),
                          "offset": offset})

        manifest = {
            "name": project,
            "version": version,
            "new_install_prompt_erase": True,
            "builds": [{"chipFamily": chip, "parts": parts}],
        }
        name = "manifest-%s.json" % b["env"]
        (out / name).write_text(json.dumps(manifest, indent=2) + "\n")
        boards.append(dict(b, manifest=name, chip=chip))
        print("%-14s %s" % (b["env"], ", ".join("0x%x" % p["offset"] for p in parts)))

    index = {
        "project": project,
        "version": version,
        "repository": config_value(cfg, "PROJECT_REPO_URL") or repo_url(),
    }
    # Credit an upstream project only when the firmware names one.
    if config_value(cfg, "UPSTREAM_PROJECT"):
        index["basedOn"] = {
            "project": config_value(cfg, "UPSTREAM_PROJECT"),
            "author": config_value(cfg, "UPSTREAM_AUTHOR") or "",
            "repository": config_value(cfg, "UPSTREAM_REPO_URL") or "",
        }
    index["setupAp"] = config_value(cfg, "AP_NAME") or ""  # "" if the project has none
    # Without Improv the installer never offers Update or Configure WiFi, so
    # the page hides the lines that promise them.
    index["improv"] = improv_enabled(cfg)
    index["boards"] = boards
    (out / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    shutil.copy2(args.page, out / "index.html")
    print("%s %s -> %s (%d boards)" % (project, version, out, len(boards)))


if __name__ == "__main__":
    main()
