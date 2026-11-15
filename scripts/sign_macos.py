#!/usr/bin/env python3
"""macOS Developer ID + notarization gate for Hertzline DMG (HZ-051).

Public mode fails closed when signing/notarization credentials are missing.
Never invents success; never recommends ad-hoc '-' for public releases.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def has_signing_identity() -> bool:
    identity = os.environ.get("APPLE_SIGNING_IDENTITY", "").strip()
    if not identity or identity == "-":
        return False
    # CI path: certificate blob + password + identity
    cert = os.environ.get("APPLE_CERTIFICATE", "")
    cert_pw = os.environ.get("APPLE_CERTIFICATE_PASSWORD", "")
    if cert and cert_pw:
        return True
    # Local Keychain: identity alone is enough for Tauri when cert is installed
    return True


def has_notarization() -> bool:
    api = all(
        os.environ.get(name)
        for name in ("APPLE_API_ISSUER", "APPLE_API_KEY", "APPLE_API_KEY_PATH")
    )
    apple_id = all(
        os.environ.get(name)
        for name in ("APPLE_ID", "APPLE_PASSWORD", "APPLE_TEAM_ID")
    )
    return api or apple_id


def credential_mode() -> str | None:
    if not has_signing_identity():
        return None
    if not has_notarization():
        return None
    if os.environ.get("APPLE_CERTIFICATE") and os.environ.get("APPLE_CERTIFICATE_PASSWORD"):
        return "ci-p12+notarize"
    return "keychain+notarize"


def list_artifacts(directory: Path) -> list[Path]:
    return sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".dmg"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        required=True,
        help="Directory of .dmg artifacts",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Fail closed if Developer ID + notarization credentials are missing",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only report credential mode; do not invoke Apple tools",
    )
    args = parser.parse_args()
    directory = args.artifacts.resolve()
    mode = credential_mode()

    if args.public and mode is None:
        print(
            "FAIL public macOS signing/notarization credentials missing "
            "(need APPLE_SIGNING_IDENTITY that is not '-', plus notarization via "
            "APPLE_API_ISSUER/APPLE_API_KEY/APPLE_API_KEY_PATH or "
            "APPLE_ID/APPLE_PASSWORD/APPLE_TEAM_ID). "
            "See macos/SIGNING.md. Owner must supply Apple Program + cert; "
            "never publish ad-hoc or unsigned DMGs."
        )
        return 1

    if mode is None:
        print(
            "unavailable: no macOS Developer ID + notarization credentials in environment "
            "(local unsigned/ad-hoc builds only; do not publish)"
        )
        return 0 if not args.public else 1

    print(f"PASS credential mode={mode}")
    if args.check_only:
        return 0

    if not directory.is_dir():
        print(f"FAIL artifacts directory missing: {directory}")
        return 1

    files = list_artifacts(directory)
    if not files:
        print(f"FAIL no .dmg in {directory}")
        return 1

    # Signing and notarization happen during `tauri build` when env is set.
    # This gate confirms credentials for release jobs that already produced DMGs.
    print(
        "PASS credentials present; signing/notarization are performed by "
        "tauri build on a Mac (see macos/SIGNING.md). "
        f"Artifacts: {', '.join(p.name for p in files)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
