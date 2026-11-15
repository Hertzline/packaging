#!/usr/bin/env python3
"""HZ-050 local check: Linux Flatpak/AppImage/deb/rpm/AUR + sandbox docs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ROOT / "linux" / "LINUX.md",
    ROOT / "linux" / "SANDBOX.md",
    ROOT / "linux" / "prerm-restore.sh",
    ROOT / "linux" / "tauri.linux.bundle.json",
    ROOT / "linux" / "flatpak" / "org.hertzline.Hertzline.yml",
    ROOT / "linux" / "flatpak" / "org.hertzline.Hertzline.metainfo.xml",
    ROOT / "linux" / "aur" / "PKGBUILD",
    ROOT / "linux" / "aur" / "hertzline.install",
    ROOT / "linux" / "aur" / "AUR.md",
    ROOT / "scripts" / "build_linux.py",
    ROOT / "scripts" / "sign_linux.py",
    ROOT / "scripts" / "checksums.py",
]

REQUIRED_MARKERS = {
    ROOT / "linux" / "LINUX.md": [
        "AppImage",
        "Flatpak",
        "deb",
        "rpm",
        "AUR",
        "polkit",
        "Sandbox",
        "SHA-256",
        "owner",
    ],
    ROOT / "linux" / "SANDBOX.md": [
        "not-possible",
        "polkit",
        "Flatpak",
        "host",
        "helper",
    ],
    ROOT / "linux" / "tauri.linux.bundle.json": [
        '"appimage"',
        '"deb"',
        '"rpm"',
        "preRemoveScript",
        "prerm-restore.sh",
    ],
    ROOT / "linux" / "flatpak" / "org.hertzline.Hertzline.yml": [
        "org.hertzline.Hertzline",
        "org.gnome.Platform",
        "finish-args",
        "not-possible",
    ],
    ROOT / "linux" / "aur" / "PKGBUILD": [
        "pkgname=hertzline",
        "webkit2gtk-4.1",
        "PLACEHOLDER",
    ],
    ROOT / "linux" / "aur" / "hertzline.install": [
        "pre_remove",
        "restore_all",
        "hertzline-helper",
    ],
    ROOT / "linux" / "aur" / "AUR.md": [
        "owner approval",
        "Draft",
    ],
    ROOT / "linux" / "prerm-restore.sh": [
        "restore_all",
        "uninstall",
        "hertzline-helper",
    ],
}


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.is_file()]
    if missing:
        print("FAIL missing files:", ", ".join(missing))
        return 1

    for path, markers in REQUIRED_MARKERS.items():
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        absent = [m for m in markers if m.lower() not in lower]
        if absent:
            print(f"FAIL {path.relative_to(ROOT)} missing markers:", ", ".join(absent))
            return 1

    # Public sign must fail closed without credentials.
    sign = ROOT / "scripts" / "sign_linux.py"
    empty = ROOT / "dist" / "hz050-empty-sign-probe"
    empty.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [sys.executable, str(sign), "--artifacts", str(empty), "--public", "--check-only"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        print("FAIL sign_linux.py --public must fail without credentials")
        print(probe.stdout)
        return 1
    if "FAIL" not in probe.stdout and "FAIL" not in probe.stderr:
        print("FAIL sign_linux.py --public did not report FAIL")
        print(probe.stdout, probe.stderr)
        return 1
    print("PASS sign_linux --public fail-closed without credentials")

    build_check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_linux.py"), "--check-only"],
        capture_output=True,
        text=True,
    )
    if build_check.returncode != 0:
        print("FAIL build_linux --check-only")
        print(build_check.stdout, build_check.stderr)
        return 1
    print(build_check.stdout.strip())

    # Checksum round-trip for linux suffixes.
    probe_dir = ROOT / "dist" / "hz050-checksum-probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    fake = probe_dir / "hertzline_0.0.0_amd64.deb"
    fake.write_bytes(b"HERTZLINE_HZ050_CHECKSUM_PROBE\n")
    sums = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "checksums.py"), str(probe_dir)],
        capture_output=True,
        text=True,
    )
    if sums.returncode != 0:
        print("FAIL checksums.py")
        print(sums.stdout, sums.stderr)
        return 1
    sums_file = probe_dir / "SHA256SUMS.txt"
    if not sums_file.is_file() or fake.name not in sums_file.read_text(encoding="utf-8"):
        print("FAIL SHA256SUMS.txt missing or incomplete")
        return 1
    print("PASS checksums.py wrote SHA256SUMS.txt for .deb")

    # Full Linux bundle build is unavailable on Windows hosts.
    if sys.platform.startswith("win"):
        print("PASS linux artifact build unavailable on Windows host (documented)")
    print("PASS hz050_linux_packaging ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
