#!/usr/bin/env python3
"""Build Windows MSI + NSIS installers via sibling Hertzline/app (HZ-049)."""

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
HELPER_EXE = WORKSPACE / "helper" / "target" / "release" / "hertzline-helper.exe"
MERGE_CONFIG = ROOT / "windows" / "tauri.windows.bundle.json"
DIST = ROOT / "dist" / "windows"


def read_app_version() -> str:
    conf = APP / "src-tauri" / "tauri.conf.json"
    data = json.loads(conf.read_text(encoding="utf-8"))
    return str(data.get("version") or "0.0.0")


def stage_helper_resource() -> Path | None:
    """Copy helper into packaging staging so Tauri resources can pick it up."""
    if not HELPER_EXE.is_file():
        print("WARN helper release binary missing; installers will lack co-located helper")
        print(f"     expected: {HELPER_EXE}")
        return None
    stage_dir = ROOT / "windows" / "staged"
    stage_dir.mkdir(parents=True, exist_ok=True)
    dest = stage_dir / "hertzline-helper.exe"
    shutil.copy2(HELPER_EXE, dest)
    print(f"PASS staged helper -> {dest} ({dest.stat().st_size} bytes)")
    return dest


def write_merge_config_with_helper(helper: Path | None) -> Path:
    data = json.loads(MERGE_CONFIG.read_text(encoding="utf-8"))
    resources = list(data["bundle"].get("resources") or [])
    # Paths in merge config are resolved relative to app/src-tauri.
    base_resources = [
        "../../packaging/windows/uninstall-restore.ps1",
    ]
    if helper is not None:
        base_resources.append("../../packaging/windows/staged/hertzline-helper.exe")
    data["bundle"]["resources"] = base_resources
    out = ROOT / "windows" / "tauri.windows.bundle.generated.json"
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def find_bundle_dirs(version: str) -> list[Path]:
    # Cargo target may be workspace-level (app/target) or crate-level.
    candidates = [
        APP / "target" / "release" / "bundle",
        APP / "src-tauri" / "target" / "release" / "bundle",
    ]
    found: list[Path] = []
    for base in candidates:
        if base.is_dir():
            found.append(base)
    return found


def collect_artifacts(version: str) -> list[Path]:
    artifacts: list[Path] = []
    for base in find_bundle_dirs(version):
        for sub in ("msi", "nsis"):
            folder = base / sub
            if not folder.is_dir():
                continue
            for path in folder.iterdir():
                if path.suffix.lower() in {".msi", ".exe"}:
                    artifacts.append(path)
    return artifacts


def run_tauri_build(merge: Path) -> int:
    env = os.environ.copy()
    env["CI"] = "true"
    # Relative path from app cwd to merge config.
    merge_rel = os.path.relpath(merge, APP)
    cmd = [
        "npx",
        "--no-install",
        "tauri",
        "build",
        "--bundles",
        "msi",
        "nsis",
        "--ci",
        "-c",
        merge_rel,
    ]
    print("RUN", " ".join(cmd), f"(cwd={APP})")
    return subprocess.call(cmd, cwd=str(APP), env=env, shell=os.name == "nt")


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
        help="After build, require Authenticode via sign_windows.py --public",
    )
    args = parser.parse_args()

    required = [
        MERGE_CONFIG,
        ROOT / "windows" / "nsis-hooks.nsh",
        ROOT / "windows" / "wix" / "uninstall-restore.wxs",
        ROOT / "windows" / "uninstall-restore.ps1",
        ROOT / "windows" / "SIGNING.md",
        ROOT / "windows" / "MSIX.md",
        ROOT / "windows" / "WINDOWS.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        print("FAIL missing:", ", ".join(missing))
        return 1

    if not APP.is_dir():
        print(f"FAIL sibling app repo missing: {APP}")
        return 1

    version = read_app_version()
    print(f"PASS app version={version}")
    print(f"PASS merge config={MERGE_CONFIG.relative_to(ROOT)}")

    if args.check_only:
        helper = stage_helper_resource()
        write_merge_config_with_helper(helper)
        print("PASS build_windows --check-only")
        return 0

    if os.name != "nt":
        print("FAIL Windows MSI/NSIS build requires a Windows host (WiX)")
        return 1

    helper = stage_helper_resource()
    merge = write_merge_config_with_helper(helper)
    code = run_tauri_build(merge)
    if code != 0:
        print(f"FAIL tauri build exit={code}")
        return code

    artifacts = collect_artifacts(version)
    if not artifacts:
        print("FAIL no MSI/NSIS artifacts under app target/release/bundle")
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

    sign_script = ROOT / "scripts" / "sign_windows.py"
    sign_cmd = [sys.executable, str(sign_script), "--artifacts", str(out_dir)]
    if args.public_sign:
        sign_cmd.append("--public")
    code = subprocess.call(sign_cmd)
    if code != 0:
        return code

    print(f"PASS windows build complete -> {out_dir} ({len(copied)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
