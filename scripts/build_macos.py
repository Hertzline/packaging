#!/usr/bin/env python3
"""Build macOS DMG via sibling Hertzline/app (HZ-051)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
APP = WORKSPACE / "app"
HELPER_CANDIDATES = [
    WORKSPACE / "helper" / "target" / "release" / "hertzline-helper",
    WORKSPACE / "helper" / "target" / "aarch64-apple-darwin" / "release" / "hertzline-helper",
    WORKSPACE / "helper" / "target" / "x86_64-apple-darwin" / "release" / "hertzline-helper",
]
MERGE_CONFIG = ROOT / "macos" / "tauri.macos.bundle.json"
DIST = ROOT / "dist" / "macos"


def read_app_version() -> str:
    conf = APP / "src-tauri" / "tauri.conf.json"
    data = json.loads(conf.read_text(encoding="utf-8"))
    return str(data.get("version") or "0.0.0")


def find_helper() -> Path | None:
    for path in HELPER_CANDIDATES:
        if path.is_file():
            return path
    return None


def stage_macos_extras() -> Path | None:
    """Stage helper binary for optional co-location in the app bundle."""
    stage_dir = ROOT / "macos" / "staged"
    stage_dir.mkdir(parents=True, exist_ok=True)

    helper_src = find_helper()
    if helper_src is None:
        print("WARN helper release binary missing; DMG will lack co-located helper")
        for candidate in HELPER_CANDIDATES:
            print(f"     expected: {candidate}")
        return None

    helper_dest = stage_dir / "hertzline-helper"
    shutil.copy2(helper_src, helper_dest)
    print(f"PASS staged helper -> {helper_dest} ({helper_dest.stat().st_size} bytes)")
    return helper_dest


def write_merge_config(helper: Path | None) -> Path:
    data = json.loads(MERGE_CONFIG.read_text(encoding="utf-8"))
    resources = [
        "../../packaging/macos/uninstall-restore.sh",
    ]
    files: dict[str, str] = {}
    if helper is not None:
        # Placed under Contents/MacOS next to the app binary.
        files["MacOS/hertzline-helper"] = "../../packaging/macos/staged/hertzline-helper"
    data["bundle"]["resources"] = resources
    data["bundle"]["macOS"]["files"] = files
    out = ROOT / "macos" / "tauri.macos.bundle.generated.json"
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def find_bundle_dirs() -> list[Path]:
    candidates = [
        APP / "target" / "release" / "bundle",
        APP / "src-tauri" / "target" / "release" / "bundle",
        APP / "target" / "aarch64-apple-darwin" / "release" / "bundle",
        APP / "target" / "x86_64-apple-darwin" / "release" / "bundle",
        APP / "src-tauri" / "target" / "aarch64-apple-darwin" / "release" / "bundle",
        APP / "src-tauri" / "target" / "x86_64-apple-darwin" / "release" / "bundle",
    ]
    return [base for base in candidates if base.is_dir()]


def collect_artifacts() -> list[Path]:
    artifacts: list[Path] = []
    for base in find_bundle_dirs():
        folder = base / "dmg"
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".dmg":
                artifacts.append(path)
    return artifacts


def run_tauri_build(merge: Path) -> int:
    env = os.environ.copy()
    env["CI"] = "true"
    merge_rel = os.path.relpath(merge, APP)
    cmd = [
        "npx",
        "--no-install",
        "tauri",
        "build",
        "--bundles",
        "dmg",
        "--ci",
        "-c",
        merge_rel,
    ]
    print("RUN", " ".join(cmd), f"(cwd={APP})")
    return subprocess.call(cmd, cwd=str(APP), env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate layout and merge config without compiling",
    )
    parser.add_argument(
        "--public-sign",
        action="store_true",
        help="After build, require Developer ID + notarization via sign_macos.py --public",
    )
    args = parser.parse_args()

    required = [
        MERGE_CONFIG,
        ROOT / "macos" / "uninstall-restore.sh",
        ROOT / "macos" / "MACOS.md",
        ROOT / "macos" / "SIGNING.md",
        ROOT / "macos" / "homebrew" / "hertzline.rb",
        ROOT / "macos" / "homebrew" / "CASK.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        print("FAIL missing:", ", ".join(missing))
        return 1

    print(f"PASS merge config={MERGE_CONFIG.relative_to(ROOT)}")

    if args.check_only:
        if APP.is_dir():
            version = read_app_version()
            print(f"PASS app version={version}")
        else:
            print(
                "WARN sibling app repo missing; layout-only check "
                "(CI packaging checkout)"
            )
        helper = stage_macos_extras()
        write_merge_config(helper)
        print("PASS build_macos --check-only")
        return 0

    if not APP.is_dir():
        print(f"FAIL sibling app repo missing: {APP}")
        return 1

    if sys.platform != "darwin":
        print("FAIL macOS DMG build requires a macOS host (Apple toolchain)")
        return 1

    version = read_app_version()
    print(f"PASS app version={version}")

    helper = stage_macos_extras()
    merge = write_merge_config(helper)
    code = run_tauri_build(merge)
    if code != 0:
        print(f"FAIL tauri build exit={code}")
        return code

    artifacts = collect_artifacts()
    if not artifacts:
        print("FAIL no .dmg artifacts under app target/*/release/bundle/dmg")
        return 1

    out_dir = DIST / version
    out_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in artifacts:
        dest = out_dir / src.name
        shutil.copy2(src, dest)
        copied.append(dest)
        print(f"PASS artifact {dest} ({dest.stat().st_size} bytes)")

    checksum_script = ROOT / "scripts" / "checksums.py"
    code = subprocess.call([sys.executable, str(checksum_script), str(out_dir)])
    if code != 0:
        return code

    sign_script = ROOT / "scripts" / "sign_macos.py"
    sign_cmd = [sys.executable, str(sign_script), "--artifacts", str(out_dir)]
    if args.public_sign:
        sign_cmd.append("--public")
    code = subprocess.call(sign_cmd)
    if code != 0:
        return code

    print(f"PASS macos build complete -> {out_dir} ({len(copied)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
