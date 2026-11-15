#!/usr/bin/env python3
"""HZ-059 local check: v1.0.0 RC packaging gates (no store/winget PR)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
APP = WORKSPACE / "app"
WEBSITE = WORKSPACE / "website"
VERSION = "1.0.0"
PACKAGE_ID = "Hertzline.Hertzline"
MANIFEST_DIR = (
    ROOT / "winget" / "manifests" / "h" / "Hertzline" / "Hertzline" / VERSION
)
DIST_WIN = ROOT / "dist" / "windows" / VERSION

REQUIRED_FILES = [
    ROOT / "release" / "HZ059_RC.md",
    ROOT / "release" / "RELEASE_FEED.md",
    ROOT / "scripts" / "prepare_rc_winget.py",
    ROOT / "scripts" / "msi_product_code.py",
    ROOT / "scripts" / "write_release_metadata.py",
    ROOT / "scripts" / "sign_windows.py",
    ROOT / "scripts" / "checksums.py",
    MANIFEST_DIR / f"{PACKAGE_ID}.yaml",
    MANIFEST_DIR / f"{PACKAGE_ID}.locale.en-US.yaml",
    MANIFEST_DIR / f"{PACKAGE_ID}.installer.yaml",
]

DOC_MARKERS = {
    ROOT / "release" / "HZ059_RC.md": [
        "1.0.0",
        "fail closed",
        "not_released",
        "HZ-054",
        "Vercel",
        "sign_windows.py",
        "write_release_metadata.py",
        "owner",
    ],
}


def fail(msg: str) -> int:
    print(f"FAIL {msg}")
    return 1


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.is_file()]
    if missing:
        return fail("missing files: " + ", ".join(missing))

    for path, markers in DOC_MARKERS.items():
        lower = path.read_text(encoding="utf-8").lower()
        absent = [m for m in markers if m.lower() not in lower]
        if absent:
            return fail(f"{path.relative_to(ROOT)} missing markers: {', '.join(absent)}")

    # App version + changelog (sibling).
    if APP.is_dir():
        conf = json.loads(
            (APP / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
        )
        if conf.get("version") != VERSION:
            return fail(f"app tauri.conf.json version must be {VERSION}")
        changelog = (APP / "CHANGELOG.md").read_text(encoding="utf-8")
        if f"[{VERSION}]" not in changelog:
            return fail("app/CHANGELOG.md missing [1.0.0] section")
        print(f"PASS app version={VERSION} changelog=1")
    else:
        print("UNAVAILABLE sibling app (CI packaging-only checkout); skip version assert")

    # Website must stay not_released until signed public assets exist.
    releases_path = WEBSITE / "src" / "data" / "releases.json"
    if releases_path.is_file():
        releases = json.loads(releases_path.read_text(encoding="utf-8"))
        if releases.get("status") != "not_released":
            return fail(
                "website releases.json must stay not_released until signed public assets"
            )
        if releases.get("wingetPublished") is True:
            return fail("wingetPublished must stay false until HZ-054")
        if releases.get("latest") is not None:
            return fail("not_released latest must be null")
        for os_key in ("windows", "linux", "macos"):
            if releases.get("artifacts", {}).get(os_key):
                return fail(f"not_released artifacts.{os_key} must be empty")
        ui_en = (releases.get("ui") or {}).get("en") or {}
        if "1.0.0" not in ui_en.get("notReleased", ""):
            return fail("website notReleased copy must mention RC 1.0.0 readiness")
        print("PASS website releases.json not_released (honest empty downloads)")
    else:
        print("UNAVAILABLE sibling website; skip releases.json assert")

    # Windows artifacts + checksums when present (dist/ is gitignored; CI may lack them).
    if DIST_WIN.is_dir() and (DIST_WIN / "SHA256SUMS.txt").is_file():
        sums = DIST_WIN / "SHA256SUMS.txt"
        msis = list(DIST_WIN.glob("Hertzline_*_x64_en-US.msi"))
        setups = list(DIST_WIN.glob("Hertzline_*_x64-setup.exe"))
        if not msis or not setups:
            return fail("dist/windows/1.0.0 needs MSI and NSIS setup.exe")
        sums_text = sums.read_text(encoding="utf-8")
        for art in msis + setups:
            if art.name not in sums_text:
                return fail(f"SHA256SUMS missing {art.name}")
            print(f"PASS artifact {art.name} ({art.stat().st_size} bytes)")
    else:
        print(
            "UNAVAILABLE dist/windows/1.0.0 "
            "(build locally with build_windows.py; dist/ is gitignored)"
        )

    # Public signing must fail closed without credentials.
    probe = ROOT / "dist" / "hz059-empty-sign-probe"
    probe.mkdir(parents=True, exist_ok=True)
    sign = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "sign_windows.py"),
            "--public",
            "--artifacts",
            str(probe),
        ],
        capture_output=True,
        text=True,
    )
    out = (sign.stdout or "") + (sign.stderr or "")
    if sign.returncode == 0:
        return fail("sign_windows --public must fail closed without credentials")
    if "fail" not in out.lower():
        return fail("sign_windows --public output must state failure")
    print("PASS sign_windows --public fail-closed")

    # winget 1.0.0 structural + validate
    version_text = (MANIFEST_DIR / f"{PACKAGE_ID}.yaml").read_text(encoding="utf-8")
    installer_text = (
        MANIFEST_DIR / f"{PACKAGE_ID}.installer.yaml"
    ).read_text(encoding="utf-8")
    locale_text = (
        MANIFEST_DIR / f"{PACKAGE_ID}.locale.en-US.yaml"
    ).read_text(encoding="utf-8")
    if f"PackageVersion: {VERSION}" not in version_text:
        return fail("winget version PackageVersion must be 1.0.0")
    if "InstallerType: wix" not in installer_text:
        return fail("winget installer must be wix")
    if f"v{VERSION}/" not in installer_text:
        return fail("InstallerUrl must target v1.0.0 GitHub Release path")
    if "winget install Hertzline.Hertzline" not in locale_text:
        return fail("locale must document winget install Hertzline.Hertzline")
    if not re.search(r"InstallerSha256:\s*[0-9A-Fa-f]{64}", installer_text):
        return fail("InstallerSha256 missing/invalid")
    if not re.search(r"ProductCode:\s*'\{[0-9A-Fa-f-]{36}\}'", installer_text):
        return fail("ProductCode missing/invalid")
    print(f"PASS winget manifests {MANIFEST_DIR.relative_to(ROOT).as_posix()}")

    winget = shutil.which("winget")
    if winget is None:
        print("UNAVAILABLE winget validate (CLI not on PATH; structural checks passed)")
    else:
        validate = subprocess.run(
            [winget, "validate", "--manifest", str(MANIFEST_DIR)],
            capture_output=True,
            text=True,
        )
        vout = (validate.stdout or "") + (validate.stderr or "")
        print(vout.strip())
        lowered = vout.lower()
        if "manifest validation failed" in lowered or "no manifest file found" in lowered:
            return fail("winget validate reported failure")
        if "manifest validation succeeded" not in lowered:
            return fail(f"winget validate unexpected exit={validate.returncode}")
        print("PASS winget validate 1.0.0")

    # Linux/macOS RC builds are host-gated.
    if sys.platform.startswith("linux"):
        linux_dist = ROOT / "dist" / "linux" / VERSION
        if linux_dist.is_dir() and (linux_dist / "SHA256SUMS.txt").is_file():
            print("PASS linux dist/1.0.0 present")
        else:
            print("UNAVAILABLE linux dist/1.0.0 on this host")
    elif sys.platform == "darwin":
        mac_dist = ROOT / "dist" / "macos" / VERSION
        if mac_dist.is_dir() and (mac_dist / "SHA256SUMS.txt").is_file():
            print("PASS macos dist/1.0.0 present")
        else:
            print("UNAVAILABLE macos dist/1.0.0 on this host")
    else:
        print("UNAVAILABLE linux/macos full RC bundles on Windows host (documented)")

    print("PASS check_hz059")
    return 0


if __name__ == "__main__":
    sys.exit(main())
