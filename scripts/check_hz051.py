#!/usr/bin/env python3
"""HZ-051 local check: macOS DMG + notarization docs + Homebrew cask draft."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ROOT / "macos" / "MACOS.md",
    ROOT / "macos" / "SIGNING.md",
    ROOT / "macos" / "uninstall-restore.sh",
    ROOT / "macos" / "tauri.macos.bundle.json",
    ROOT / "macos" / "homebrew" / "hertzline.rb",
    ROOT / "macos" / "homebrew" / "CASK.md",
    ROOT / "scripts" / "build_macos.py",
    ROOT / "scripts" / "sign_macos.py",
    ROOT / "scripts" / "checksums.py",
]

REQUIRED_MARKERS = {
    ROOT / "macos" / "MACOS.md": [
        "DMG",
        "notariz",
        "$99",
        "Homebrew",
        "SHA-256",
        "owner",
        "SMAppService",
        "13.0",
    ],
    ROOT / "macos" / "SIGNING.md": [
        "fail closed",
        "Developer ID",
        "notariz",
        "never skip",
        "ad-hoc",
    ],
    ROOT / "macos" / "tauri.macos.bundle.json": [
        '"dmg"',
        "minimumSystemVersion",
        "13.0",
        "uninstall-restore.sh",
    ],
    ROOT / "macos" / "homebrew" / "hertzline.rb": [
        'cask "hertzline"',
        "PLACEHOLDER",
        "Hertzline.app",
        "ventura",
    ],
    ROOT / "macos" / "homebrew" / "CASK.md": [
        "owner approval",
        "Draft",
        "PLACEHOLDER",
    ],
    ROOT / "macos" / "uninstall-restore.sh": [
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
    sign = ROOT / "scripts" / "sign_macos.py"
    empty = ROOT / "dist" / "hz051-empty-sign-probe"
    empty.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [sys.executable, str(sign), "--artifacts", str(empty), "--public", "--check-only"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        print("FAIL sign_macos.py --public must fail without credentials")
        print(probe.stdout)
        return 1
    if "FAIL" not in probe.stdout and "FAIL" not in probe.stderr:
        print("FAIL sign_macos.py --public did not report FAIL")
        print(probe.stdout, probe.stderr)
        return 1
    print("PASS sign_macos --public fail-closed without credentials")

    build_check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_macos.py"), "--check-only"],
        capture_output=True,
        text=True,
    )
    if build_check.returncode != 0:
        print("FAIL build_macos --check-only")
        print(build_check.stdout, build_check.stderr)
        return 1
    print(build_check.stdout.strip())

    # Checksum round-trip for .dmg suffix.
    probe_dir = ROOT / "dist" / "hz051-checksum-probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    fake = probe_dir / "Hertzline_0.0.0_aarch64.dmg"
    fake.write_bytes(b"HERTZLINE_HZ051_CHECKSUM_PROBE\n")
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
    print("PASS checksums.py wrote SHA256SUMS.txt for .dmg")

    # Full DMG build is unavailable off macOS hosts.
    if sys.platform != "darwin":
        print("PASS macos artifact build unavailable on non-macOS host (documented)")
    print("PASS hz051_macos_packaging ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
