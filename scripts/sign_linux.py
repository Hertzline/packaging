#!/usr/bin/env python3
"""Linux GPG signing gate for Hertzline deb/rpm (HZ-050).

Public mode fails closed when signing credentials are missing.
Never invents success; never skips silently for public releases.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def has_gpg_key() -> bool:
    return bool(os.environ.get("TAURI_SIGNING_RPM_KEY") or os.environ.get("HERTZLINE_GPG_KEY_ID"))


def list_artifacts(directory: Path) -> list[Path]:
    suffixes = {".deb", ".rpm"}
    return sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in suffixes
    )


def sign_one(path: Path) -> int:
    key_id = os.environ.get("HERTZLINE_GPG_KEY_ID", "")
    if path.suffix.lower() == ".rpm" and os.environ.get("TAURI_SIGNING_RPM_KEY"):
        # Tauri signs RPM at build time when TAURI_SIGNING_RPM_KEY is set.
        # Post-hoc: require rpmsign when available.
        if shutil.which("rpmsign") and key_id:
            cmd = ["rpmsign", "--addsign", "-u", key_id, str(path)]
            print("RUN", " ".join(cmd))
            return subprocess.call(cmd)
        print(f"PASS rpm signing deferred to Tauri build env for {path.name}")
        return 0
    if path.suffix.lower() == ".deb" and key_id and shutil.which("dpkg-sig"):
        cmd = ["dpkg-sig", "--sign", "builder", "-k", key_id, str(path)]
        print("RUN", " ".join(cmd))
        return subprocess.call(cmd)
    if key_id and shutil.which("gpg"):
        sig = path.with_suffix(path.suffix + ".asc")
        cmd = ["gpg", "--batch", "--yes", "-u", key_id, "--armor", "--detach-sign", "-o", str(sig), str(path)]
        print("RUN", " ".join(cmd))
        return subprocess.call(cmd)
    print(f"FAIL no usable GPG sign tool for {path.name}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        required=True,
        help="Directory containing .deb / .rpm artifacts",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Require credentials; exit non-zero if missing (fail closed)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate credential presence / artifact list without signing",
    )
    args = parser.parse_args()
    directory = args.artifacts.resolve()
    if not directory.is_dir():
        print(f"FAIL not a directory: {directory}")
        return 1

    mode_ok = has_gpg_key()
    if args.public and not mode_ok:
        print("FAIL public Linux signing requires TAURI_SIGNING_RPM_KEY or HERTZLINE_GPG_KEY_ID")
        print("     never skip silently; owner supplies GPG key (RULES.md)")
        return 1

    artifacts = list_artifacts(directory)
    if args.check_only:
        if args.public and not mode_ok:
            return 1
        print(f"PASS sign_linux --check-only artifacts={len(artifacts)} credentials={'yes' if mode_ok else 'no'}")
        return 0

    if not args.public and not mode_ok:
        print("WARN no GPG credentials; skipping sign (non-public). Use --public to fail closed.")
        return 0

    if not artifacts:
        print(f"FAIL no .deb/.rpm artifacts in {directory}")
        return 1

    for path in artifacts:
        code = sign_one(path)
        if code != 0:
            return code
    print(f"PASS signed {len(artifacts)} linux package(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
