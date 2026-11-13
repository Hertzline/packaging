#!/usr/bin/env python3
"""HZ-008 local check: D5 spike docs and decision markers present."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D5 = ROOT / "spikes" / "D5.md"

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / "NOTICE",
    D5,
    ROOT / ".github" / "workflows" / "ci.yml",
]

REQUIRED_SUBSTRINGS = [
    "Azure Artifact Signing",
    "$9.99",
    "$99",
    "Apple Developer Program",
    "Flatpak",
    "AppImage",
    "MSI",
    "NSIS",
    "winget",
    "Hertzline.Hertzline",
    "owner approval",
    "never skip signing",
    "**chosen**",
]


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.is_file()]
    if missing:
        print("FAIL missing files:", ", ".join(missing))
        return 1

    text = D5.read_text(encoding="utf-8")
    absent = [s for s in REQUIRED_SUBSTRINGS if s not in text]
    if absent:
        print("FAIL D5.md missing markers:", ", ".join(absent))
        return 1

    if "Status recorded" not in text and "decided" not in text.lower():
        print("FAIL D5.md missing decision status")
        return 1

    print("PASS d5_check ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
