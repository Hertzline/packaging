#!/usr/bin/env python3
"""HZ-049 local check: Windows MSI/NSIS scripts, signing fail-closed, AC-7.3 hooks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ROOT / "windows" / "WINDOWS.md",
    ROOT / "windows" / "SIGNING.md",
    ROOT / "windows" / "MSIX.md",
    ROOT / "windows" / "nsis-hooks.nsh",
    ROOT / "windows" / "wix" / "uninstall-restore.wxs",
    ROOT / "windows" / "tauri.windows.bundle.json",
    ROOT / "windows" / "uninstall-restore.ps1",
    ROOT / "scripts" / "build_windows.py",
    ROOT / "scripts" / "build_msix.py",
    ROOT / "scripts" / "checksums.py",
    ROOT / "scripts" / "sign_windows.py",
]

REQUIRED_MARKERS = {
    ROOT / "windows" / "SIGNING.md": [
        "fail closed",
        "Artifact Signing",
        "never skip",
        "--no-sign",
    ],
    ROOT / "windows" / "nsis-hooks.nsh": [
        "NSIS_HOOK_PREUNINSTALL",
        "restore_all",
        "uninstall",
    ],
    ROOT / "windows" / "wix" / "uninstall-restore.wxs": [
        "HertzlineRestoreAll",
        "restore_all",
        "RemoveFiles",
        "HertzlineRestoreMarker",
    ],
    ROOT / "windows" / "tauri.windows.bundle.json": [
        '"msi"',
        '"nsis"',
        "installerHooks",
        "fragmentPaths",
        "HertzlineRestoreMarker",
    ],
    ROOT / "windows" / "MSIX.md": [
        "optional",
        "Store",
        "not possible",
    ],
    ROOT / "windows" / "WINDOWS.md": [
        "SHA-256",
        "AC-7.3",
        "MSI",
        "NSIS",
    ],
}


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.is_file()]
    if missing:
        print("FAIL missing files:", ", ".join(missing))
        return 1

    for path, markers in REQUIRED_MARKERS.items():
        text = path.read_text(encoding="utf-8")
        # case-insensitive for docs that may use "Never skip"
        lower = text.lower()
        absent = [m for m in markers if m.lower() not in lower]
        if absent:
            print(f"FAIL {path.relative_to(ROOT)} missing markers:", ", ".join(absent))
            return 1

    # Public sign must fail closed without credentials.
    sign = ROOT / "scripts" / "sign_windows.py"
    empty = ROOT / "dist" / "hz049-empty-sign-probe"
    empty.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [sys.executable, str(sign), "--artifacts", str(empty), "--public", "--check-only"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        print("FAIL sign_windows.py --public must fail without credentials")
        print(probe.stdout)
        return 1
    if "FAIL" not in probe.stdout and "FAIL" not in probe.stderr:
        print("FAIL sign_windows.py --public did not report FAIL")
        print(probe.stdout, probe.stderr)
        return 1
    print("PASS sign_windows --public fail-closed without credentials")

    build_check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_windows.py"), "--check-only"],
        capture_output=True,
        text=True,
    )
    if build_check.returncode != 0:
        print("FAIL build_windows --check-only")
        print(build_check.stdout, build_check.stderr)
        return 1
    print(build_check.stdout.strip())

    msix = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_msix.py")],
        capture_output=True,
        text=True,
    )
    if msix.returncode != 0 or "unavailable" not in msix.stdout.lower():
        print("FAIL build_msix stub")
        print(msix.stdout, msix.stderr)
        return 1
    print("PASS build_msix stub unavailable (honest)")

    # Checksum round-trip on a tiny fake artifact.
    probe_dir = ROOT / "dist" / "hz049-checksum-probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    fake = probe_dir / "Hertzline_0.0.0_x64_en-US.msi"
    fake.write_bytes(b"HERTZLINE_HZ049_CHECKSUM_PROBE\n")
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
    print("PASS checksums.py wrote SHA256SUMS.txt")

    print("PASS hz049_windows_packaging ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
