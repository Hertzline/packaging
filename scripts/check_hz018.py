#!/usr/bin/env python3
"""HZ-018 local check: uninstall hooks invoke helper restore_all."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = [
    ROOT / "windows" / "uninstall-restore.ps1",
    ROOT / "linux" / "prerm-restore.sh",
    ROOT / "macos" / "uninstall-restore.sh",
]

REQUIRED_MARKERS = [
    "restore_all",
    "uninstall",
]


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in SCRIPTS if not p.is_file()]
    if missing:
        print("FAIL missing uninstall scripts:", ", ".join(missing))
        return 1

    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        absent = [m for m in REQUIRED_MARKERS if m not in text]
        if absent:
            print(f"FAIL {path.relative_to(ROOT)} missing markers:", ", ".join(absent))
            return 1
        if "hertzline-helper" not in text and "HelperPath" not in text:
            print(f"FAIL {path.relative_to(ROOT)} does not invoke hertzline-helper")
            return 1

    print("PASS hz018_uninstall_hooks ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
