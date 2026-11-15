#!/usr/bin/env python3
"""HZ-059: write winget 1.0.0 manifests from a local Windows MSI + SHA256SUMS.

Does not open a winget-pkgs PR. InstallerUrl points at the future GitHub
Release asset path for v1.0.0; URL is not live until the owner publishes
signed artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msi_product_code import read_msi_property  # noqa: E402
PACKAGE_ID = "Hertzline.Hertzline"
VERSION = "1.0.0"
MANIFEST_DIR = (
    ROOT / "winget" / "manifests" / "h" / "Hertzline" / "Hertzline" / VERSION
)
CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_sums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(\S.+)", line)
        if not match:
            raise ValueError(f"bad sums line: {line}")
        out[match.group(2).strip()] = match.group(1).upper()
    return out


def write_manifests(
    *,
    msi_name: str,
    sha256: str,
    product_code: str,
    upgrade_code: str,
) -> None:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    url = (
        f"https://github.com/Hertzline/app/releases/download/v{VERSION}/{msi_name}"
    )

    version_yaml = f"""# yaml-language-server: $schema=https://aka.ms/winget-manifest.version.1.12.0.schema.json
PackageIdentifier: {PACKAGE_ID}
PackageVersion: {VERSION}
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.12.0
"""
    locale_yaml = f"""# yaml-language-server: $schema=https://aka.ms/winget-manifest.defaultLocale.1.12.0.schema.json
PackageIdentifier: {PACKAGE_ID}
PackageVersion: {VERSION}
PackageLocale: en-US
Publisher: Hertzline
PublisherUrl: https://github.com/Hertzline
PublisherSupportUrl: https://github.com/Hertzline/app/issues
Author: Hertzline
PackageName: Hertzline
PackageUrl: https://github.com/Hertzline/app
License: MIT
LicenseUrl: https://github.com/Hertzline/app/blob/main/LICENSE
Copyright: Copyright (c) Hertzline
ShortDescription: Measured, reversible game and desktop smoothing
Description: Hertzline measures frame times and hardware stats on your machine, then applies only reversible optimizations you choose. Every change shows what it does, expected effect, risk, and how to undo it. No placebo tweaks, no injection, no invented FPS claims.
Moniker: hertzline
Tags:
- gaming
- performance
- benchmark
- fps
- frame-time
- optimization
- reversible
InstallationNotes: Install with winget install Hertzline.Hertzline. Public releases must be Authenticode-signed; do not submit this RC draft to winget-pkgs without owner approval (HZ-054).
Documentations:
- DocumentLabel: Documentation
  DocumentUrl: https://github.com/Hertzline/website
- DocumentLabel: Security
  DocumentUrl: https://github.com/Hertzline/.github/blob/main/SECURITY.md
ManifestType: defaultLocale
ManifestVersion: 1.12.0
"""
    installer_yaml = f"""# yaml-language-server: $schema=https://aka.ms/winget-manifest.installer.1.12.0.schema.json
PackageIdentifier: {PACKAGE_ID}
PackageVersion: {VERSION}
Platform:
- Windows.Desktop
MinimumOSVersion: 10.0.19041.0
InstallerType: wix
Scope: machine
InstallModes:
- interactive
- silent
- silentWithProgress
UpgradeBehavior: install
Commands:
- hertzline
Installers:
- Architecture: x64
  InstallerUrl: {url}
  InstallerSha256: {sha256}
  ProductCode: '{product_code}'
  AppsAndFeaturesEntries:
  - DisplayName: Hertzline
    Publisher: hertzline
    ProductCode: '{product_code}'
    UpgradeCode: '{upgrade_code}'
    InstallerType: wix
ManifestType: installer
ManifestVersion: 1.12.0
"""

    (MANIFEST_DIR / f"{PACKAGE_ID}.yaml").write_text(version_yaml, encoding="utf-8")
    (MANIFEST_DIR / f"{PACKAGE_ID}.locale.en-US.yaml").write_text(
        locale_yaml, encoding="utf-8"
    )
    (MANIFEST_DIR / f"{PACKAGE_ID}.installer.yaml").write_text(
        installer_yaml, encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=ROOT / "dist" / "windows" / VERSION,
        help="Directory with MSI + SHA256SUMS.txt",
    )
    args = parser.parse_args()
    artifacts = args.artifacts.resolve()
    if not artifacts.is_dir():
        print(f"FAIL missing artifacts dir: {artifacts}")
        return 1

    sums_path = artifacts / "SHA256SUMS.txt"
    if not sums_path.is_file():
        print(f"FAIL missing {sums_path}")
        return 1

    try:
        sums = parse_sums(sums_path)
    except ValueError as exc:
        print(f"FAIL {exc}")
        return 1

    msi_candidates = sorted(artifacts.glob("Hertzline_*_x64_en-US.msi"))
    if not msi_candidates:
        print("FAIL no Hertzline_*_x64_en-US.msi in artifacts dir")
        return 1
    msi = msi_candidates[0]
    msi_name = msi.name
    if msi_name not in sums:
        print(f"FAIL {msi_name} missing from SHA256SUMS.txt")
        return 1

    file_sha = sha256_file(msi)
    if file_sha != sums[msi_name]:
        print(
            f"FAIL SHA mismatch for {msi_name}: "
            f"file={file_sha} sums={sums[msi_name]}"
        )
        return 1

    try:
        product_code = read_msi_property(msi, "ProductCode")
        upgrade_code = read_msi_property(msi, "UpgradeCode")
    except RuntimeError as exc:
        print(f"FAIL {exc}")
        return 1

    if not re.fullmatch(r"\{[0-9A-Fa-f-]{36}\}", product_code):
        print(f"FAIL bad ProductCode: {product_code}")
        return 1
    if not re.fullmatch(r"\{[0-9A-Fa-f-]{36}\}", upgrade_code):
        print(f"FAIL bad UpgradeCode: {upgrade_code}")
        return 1

    write_manifests(
        msi_name=msi_name,
        sha256=file_sha,
        product_code=product_code,
        upgrade_code=upgrade_code,
    )
    print(f"PASS wrote {MANIFEST_DIR.relative_to(ROOT).as_posix()}")
    print(f"PASS MSI {msi_name} sha256={file_sha}")
    print(f"PASS ProductCode={product_code}")
    print("NOTE InstallerUrl is not live until owner publishes signed v1.0.0 assets")
    print("NOTE do not open winget-pkgs PR without owner approval (HZ-054)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
