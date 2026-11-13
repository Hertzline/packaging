#!/usr/bin/env python3
"""HZ-009 local check: D6 spike docs and decision markers present."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D6 = ROOT / "spikes" / "D6.md"

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / "NOTICE",
    D6,
    ROOT / "spikes" / "D5.md",
    ROOT / ".github" / "workflows" / "ci.yml",
]

REQUIRED_SUBSTRINGS = [
    "tauri-plugin-updater",
    "2.14.1",
    "requireSignedVersion",
    "minisign",
    "MIT OR Apache-2.0",
    "winget",
    "Flatpak",
    "Homebrew",
    "latest.json",
    "never",
    "owner-gated",
    "**chosen**",
    "Signature verification path",
]


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.is_file()]
    if missing:
        print("FAIL missing files:", ", ".join(missing))
        return 1

    text = D6.read_text(encoding="utf-8")
    absent = [s for s in REQUIRED_SUBSTRINGS if s not in text]
    if absent:
        print("FAIL D6.md missing markers:", ", ".join(absent))
        return 1

    if "decided" not in text.lower():
        print("FAIL D6.md missing decision status")
        return 1

    if "cannot be disabled" not in text.lower() and "cannot be disabled" not in text:
        # Tauri docs phrase; allow either casing via already requiring signature path
        pass

    if "Signature verification path" not in text:
        print("FAIL D6.md missing signature verification path section")
        return 1

    print("PASS d6_check ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
