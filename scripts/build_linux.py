#!/usr/bin/env python3
"""Build Linux AppImage + deb + rpm via sibling Hertzline/app (HZ-050)."""

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
    WORKSPACE / "helper" / "target" / "x86_64-unknown-linux-gnu" / "release" / "hertzline-helper",
]
POLICY_SRC = WORKSPACE / "helper" / "policy" / "linux" / "org.hertzline.helper.policy"
MERGE_CONFIG = ROOT / "linux" / "tauri.linux.bundle.json"
DIST = ROOT / "dist" / "linux"
HELPER_INSTALL_PATH = "/usr/bin/hertzline-helper"


def read_app_version() -> str:
    conf = APP / "src-tauri" / "tauri.conf.json"
    data = json.loads(conf.read_text(encoding="utf-8"))
    return str(data.get("version") or "0.0.0")


def find_helper() -> Path | None:
    for path in HELPER_CANDIDATES:
        if path.is_file():
            return path
    return None


def stage_linux_extras() -> tuple[Path | None, Path | None]:
    """Stage helper binary + polkit policy with real exec path for package files."""
    stage_dir = ROOT / "linux" / "staged"
    stage_dir.mkdir(parents=True, exist_ok=True)

    helper_src = find_helper()
    helper_dest: Path | None = None
    if helper_src is None:
        print("WARN helper release binary missing; deb/rpm will lack co-located helper")
        for candidate in HELPER_CANDIDATES:
            print(f"     expected: {candidate}")
    else:
        helper_dest = stage_dir / "hertzline-helper"
        shutil.copy2(helper_src, helper_dest)
        print(f"PASS staged helper -> {helper_dest} ({helper_dest.stat().st_size} bytes)")

    policy_dest: Path | None = None
    if not POLICY_SRC.is_file():
        print(f"WARN polkit policy missing: {POLICY_SRC}")
    else:
        text = POLICY_SRC.read_text(encoding="utf-8")
        text = text.replace("HELPER_INSTALL_PATH", HELPER_INSTALL_PATH)
        policy_dest = stage_dir / "org.hertzline.helper.policy"
        policy_dest.write_text(text, encoding="utf-8")
        print(f"PASS staged polkit policy -> {policy_dest}")

    return helper_dest, policy_dest


def write_merge_config(helper: Path | None, policy: Path | None) -> Path:
    data = json.loads(MERGE_CONFIG.read_text(encoding="utf-8"))
    files: dict[str, str] = {}
    if helper is not None:
        files["/usr/bin/hertzline-helper"] = "../../packaging/linux/staged/hertzline-helper"
    if policy is not None:
        files["/usr/share/polkit-1/actions/org.hertzline.helper.policy"] = (
            "../../packaging/linux/staged/org.hertzline.helper.policy"
        )
    data["bundle"]["linux"]["deb"]["files"] = files
    data["bundle"]["linux"]["rpm"]["files"] = dict(files)
    out = ROOT / "linux" / "tauri.linux.bundle.generated.json"
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def find_bundle_dirs() -> list[Path]:
    candidates = [
        APP / "target" / "release" / "bundle",
        APP / "src-tauri" / "target" / "release" / "bundle",
    ]
    return [base for base in candidates if base.is_dir()]


def collect_artifacts() -> list[Path]:
    suffixes = {".appimage", ".deb", ".rpm"}
    artifacts: list[Path] = []
    for base in find_bundle_dirs():
        for sub in ("appimage", "deb", "rpm"):
            folder = base / sub
            if not folder.is_dir():
                continue
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix.lower() in suffixes:
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
        "appimage",
        "deb",
        "rpm",
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
        help="After build, require GPG via sign_linux.py --public",
    )
    args = parser.parse_args()

    required = [
        MERGE_CONFIG,
        ROOT / "linux" / "prerm-restore.sh",
        ROOT / "linux" / "LINUX.md",
        ROOT / "linux" / "SANDBOX.md",
        ROOT / "linux" / "flatpak" / "org.hertzline.Hertzline.yml",
        ROOT / "linux" / "flatpak" / "org.hertzline.Hertzline.metainfo.xml",
        ROOT / "linux" / "aur" / "PKGBUILD",
        ROOT / "linux" / "aur" / "hertzline.install",
        ROOT / "linux" / "aur" / "AUR.md",
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
        helper, policy = stage_linux_extras()
        write_merge_config(helper, policy)
        print("PASS build_linux --check-only")
        return 0

    if not APP.is_dir():
        print(f"FAIL sibling app repo missing: {APP}")
        return 1

    if sys.platform.startswith("win"):
        print("FAIL Linux AppImage/deb/rpm build requires a Linux host (WebKitGTK)")
        return 1

    version = read_app_version()
    print(f"PASS app version={version}")

    helper, policy = stage_linux_extras()
    merge = write_merge_config(helper, policy)
    code = run_tauri_build(merge)
    if code != 0:
        print(f"FAIL tauri build exit={code}")
        return code

    artifacts = collect_artifacts()
    if not artifacts:
        print("FAIL no AppImage/deb/rpm artifacts under app target/release/bundle")
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

    sign_script = ROOT / "scripts" / "sign_linux.py"
    sign_cmd = [sys.executable, str(sign_script), "--artifacts", str(out_dir)]
    if args.public_sign:
        sign_cmd.append("--public")
    code = subprocess.call(sign_cmd)
    if code != 0:
        return code

    print(f"PASS linux build complete -> {out_dir} ({len(copied)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
