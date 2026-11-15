#!/usr/bin/env python3
"""Windows Authenticode gate for Hertzline installers (HZ-049).

Public mode fails closed when signing credentials are missing.
Never invents success; never recommends tauri --no-sign for releases.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ARTIFACT_ENV = (
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_TENANT_ID",
    "HERTZLINE_ARTIFACT_SIGNING_ENDPOINT",
    "HERTZLINE_ARTIFACT_SIGNING_ACCOUNT",
    "HERTZLINE_ARTIFACT_SIGNING_PROFILE",
)


def has_artifact_signing() -> bool:
    return all(os.environ.get(name) for name in ARTIFACT_ENV)


def has_ov_thumbprint() -> bool:
    return bool(os.environ.get("HERTZLINE_WINDOWS_CERT_THUMBPRINT"))


def has_custom_sign_command() -> bool:
    cmd = os.environ.get("HERTZLINE_WINDOWS_SIGN_COMMAND", "")
    return "%1" in cmd


def credential_mode() -> str | None:
    if has_artifact_signing():
        return "artifact-signing"
    if has_ov_thumbprint():
        return "ov-thumbprint"
    if has_custom_sign_command():
        return "custom-sign-command"
    return None


def list_artifacts(directory: Path) -> list[Path]:
    suffixes = {".msi", ".exe"}
    return sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in suffixes and not p.name.endswith("-setup.exe.sig")
    )


def sign_one(path: Path, mode: str) -> int:
    if mode == "artifact-signing":
        endpoint = os.environ["HERTZLINE_ARTIFACT_SIGNING_ENDPOINT"]
        account = os.environ["HERTZLINE_ARTIFACT_SIGNING_ACCOUNT"]
        profile = os.environ["HERTZLINE_ARTIFACT_SIGNING_PROFILE"]
        cli = shutil.which("artifact-signing-cli")
        if not cli:
            print("FAIL artifact-signing-cli not on PATH (cargo install artifact-signing-cli)")
            return 1
        cmd = [
            cli,
            "-e",
            endpoint,
            "-a",
            account,
            "-c",
            profile,
            "-d",
            "Hertzline",
            str(path),
        ]
        print("RUN", " ".join(cmd))
        return subprocess.call(cmd)

    if mode == "ov-thumbprint":
        thumb = os.environ["HERTZLINE_WINDOWS_CERT_THUMBPRINT"]
        timestamp = os.environ.get(
            "HERTZLINE_WINDOWS_TIMESTAMP_URL",
            "http://timestamp.digicert.com",
        )
        signtool = shutil.which("signtool")
        if not signtool:
            print("FAIL signtool.exe not on PATH (Windows SDK)")
            return 1
        cmd = [
            signtool,
            "sign",
            "/fd",
            "sha256",
            "/td",
            "sha256",
            "/tr",
            timestamp,
            "/sha1",
            thumb,
            str(path),
        ]
        print("RUN", " ".join(cmd))
        return subprocess.call(cmd)

    template = os.environ["HERTZLINE_WINDOWS_SIGN_COMMAND"]
    cmd = template.replace("%1", str(path))
    print("RUN", cmd)
    return subprocess.call(cmd, shell=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        required=True,
        help="Directory of MSI/NSIS artifacts to sign",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Fail closed if credentials are missing (required for release)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only report credential mode; do not invoke sign tools",
    )
    args = parser.parse_args()
    directory = args.artifacts.resolve()
    mode = credential_mode()

    if args.public and mode is None:
        print(
            "FAIL public signing credentials missing "
            "(Artifact Signing env, HERTZLINE_WINDOWS_CERT_THUMBPRINT, "
            "or HERTZLINE_WINDOWS_SIGN_COMMAND with %1). "
            "See windows/SIGNING.md. Owner must supply cert; never use --no-sign."
        )
        return 1

    if mode is None:
        print(
            "unavailable: no Windows signing credentials in environment "
            "(local unsigned builds only; do not publish)"
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
        print(f"FAIL no .msi/.exe in {directory}")
        return 1

    for path in files:
        code = sign_one(path, mode)
        if code != 0:
            print(f"FAIL signing {path.name} exit={code}")
            return code
        print(f"PASS signed {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
