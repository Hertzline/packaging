#!/usr/bin/env python3
"""HZ-053 local check: winget multi-file manifests for Hertzline.Hertzline."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = (
    ROOT / "winget" / "manifests" / "h" / "Hertzline" / "Hertzline" / "0.0.0"
)
PACKAGE_ID = "Hertzline.Hertzline"
INSTALL_CMD = "winget install Hertzline.Hertzline"
MANIFEST_VERSION = "1.12.0"
SCHEMA_HEADER = re.compile(
    r"^# yaml-language-server: \$schema=https://aka\.ms/winget-manifest\."
    r"(version|defaultLocale|installer)\.1\.12\.0\.schema\.json\s*$"
)

REQUIRED_FILES = [
    ROOT / "winget" / "WINGET.md",
    MANIFEST_DIR / f"{PACKAGE_ID}.yaml",
    MANIFEST_DIR / f"{PACKAGE_ID}.locale.en-US.yaml",
    MANIFEST_DIR / f"{PACKAGE_ID}.installer.yaml",
]

REQUIRED_MARKERS = {
    ROOT / "winget" / "WINGET.md": [
        PACKAGE_ID,
        INSTALL_CMD,
        "1.12.0",
        "owner approval",
        "HZ-054",
        "winget validate",
        "InstallerSha256",
        "ProductCode",
    ],
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _require_fields(path: Path, text: str, fields: list[str]) -> list[str]:
    absent: list[str] = []
    for field in fields:
        if f"{field}:" not in text:
            absent.append(field)
    return absent


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.is_file()]
    if missing:
        print("FAIL missing files:", ", ".join(missing))
        return 1

    for path, markers in REQUIRED_MARKERS.items():
        text = _read(path)
        lower = text.lower()
        absent = [m for m in markers if m.lower() not in lower]
        if absent:
            print(f"FAIL {path.relative_to(ROOT)} missing markers:", ", ".join(absent))
            return 1

    version_path = MANIFEST_DIR / f"{PACKAGE_ID}.yaml"
    locale_path = MANIFEST_DIR / f"{PACKAGE_ID}.locale.en-US.yaml"
    installer_path = MANIFEST_DIR / f"{PACKAGE_ID}.installer.yaml"

    version = _read(version_path)
    locale = _read(locale_path)
    installer = _read(installer_path)

    for path, text in (
        (version_path, version),
        (locale_path, locale),
        (installer_path, installer),
    ):
        first = text.splitlines()[0] if text.splitlines() else ""
        if not SCHEMA_HEADER.match(first):
            print(f"FAIL {path.relative_to(ROOT)} missing/invalid schema header")
            print(f"  got: {first!r}")
            return 1
        if "\t" in text:
            print(f"FAIL {path.relative_to(ROOT)} contains tab characters")
            return 1

    if _require_fields(
        version_path,
        version,
        [
            "PackageIdentifier",
            "PackageVersion",
            "DefaultLocale",
            "ManifestType",
            "ManifestVersion",
        ],
    ):
        print("FAIL version manifest missing required fields")
        return 1
    if "ManifestType: version" not in version:
        print("FAIL version ManifestType must be version")
        return 1
    if f"ManifestVersion: {MANIFEST_VERSION}" not in version:
        print(f"FAIL version ManifestVersion must be {MANIFEST_VERSION}")
        return 1
    if f"PackageIdentifier: {PACKAGE_ID}" not in version:
        print("FAIL PackageIdentifier mismatch in version manifest")
        return 1
    if "PackageVersion: 0.0.0" not in version:
        print("FAIL draft PackageVersion must be 0.0.0")
        return 1
    if "DefaultLocale: en-US" not in version:
        print("FAIL DefaultLocale must be en-US")
        return 1

    locale_missing = _require_fields(
        locale_path,
        locale,
        [
            "PackageIdentifier",
            "PackageVersion",
            "PackageLocale",
            "Publisher",
            "PackageName",
            "License",
            "ShortDescription",
            "ManifestType",
            "ManifestVersion",
        ],
    )
    if locale_missing:
        print("FAIL locale missing fields:", ", ".join(locale_missing))
        return 1
    if "ManifestType: defaultLocale" not in locale:
        print("FAIL locale ManifestType must be defaultLocale")
        return 1
    if INSTALL_CMD not in locale:
        print(f"FAIL locale InstallationNotes must include `{INSTALL_CMD}`")
        return 1
    if "License: MIT" not in locale:
        print("FAIL locale License must be MIT")
        return 1
    if "PackageName: Hertzline" not in locale:
        print("FAIL locale PackageName must be Hertzline")
        return 1

    installer_missing = _require_fields(
        installer_path,
        installer,
        [
            "PackageIdentifier",
            "PackageVersion",
            "InstallerType",
            "Installers",
            "InstallerUrl",
            "InstallerSha256",
            "Architecture",
            "ProductCode",
            "ManifestType",
            "ManifestVersion",
        ],
    )
    if installer_missing:
        print("FAIL installer missing fields:", ", ".join(installer_missing))
        return 1
    if "ManifestType: installer" not in installer:
        print("FAIL installer ManifestType must be installer")
        return 1
    if "InstallerType: wix" not in installer:
        print("FAIL InstallerType must be wix (MSI via Tauri/WiX)")
        return 1
    if "Architecture: x64" not in installer:
        print("FAIL Architecture must include x64")
        return 1
    if "https://github.com/Hertzline/app/releases/download/" not in installer:
        print("FAIL InstallerUrl must use Hertzline/app GitHub Releases HTTPS URL")
        return 1
    sha_match = re.search(r"InstallerSha256:\s*([0-9A-Fa-f]{64})", installer)
    if not sha_match:
        print("FAIL InstallerSha256 must be 64 hex chars")
        return 1
    if not re.search(r"ProductCode:\s*'\{[0-9A-Fa-f-]{36}\}'", installer):
        print("FAIL ProductCode must be a braced GUID")
        return 1

    # Path partition must match PackageIdentifier (case-sensitive).
    expected_rel = Path("winget") / "manifests" / "h" / "Hertzline" / "Hertzline" / "0.0.0"
    if MANIFEST_DIR.relative_to(ROOT) != expected_rel:
        print("FAIL manifest path does not match PackageIdentifier partition")
        return 1

    print(f"PASS PackageIdentifier {PACKAGE_ID}")
    print(f"PASS install string `{INSTALL_CMD}`")
    print(f"PASS path {expected_rel.as_posix()}")

    winget = shutil.which("winget")
    if winget is None:
        print("UNAVAILABLE winget validate (winget CLI not on PATH; structural checks passed)")
        print("PASS check_hz053")
        return 0

    validate = subprocess.run(
        [winget, "validate", "--manifest", str(MANIFEST_DIR)],
        capture_output=True,
        text=True,
    )
    out = (validate.stdout or "") + (validate.stderr or "")
    print(out.strip())
    # winget returns 0 on clean success; non-zero with "succeeded with warnings"
    # is still acceptable if the word succeeded appears and "failed" does not.
    lowered = out.lower()
    if "manifest validation failed" in lowered or "no manifest file found" in lowered:
        print("FAIL winget validate reported failure")
        return 1
    if "manifest validation succeeded" not in lowered:
        print(f"FAIL winget validate unexpected exit={validate.returncode}")
        return 1
    print("PASS winget validate (schema 1.12.0)")
    print("PASS check_hz053")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
