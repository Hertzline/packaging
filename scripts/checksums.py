#!/usr/bin/env python3
"""Write SHA-256 checksums for release artifacts (HZ-049)."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing artifacts (msi, exe, etc.)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Checksum file path (default: <directory>/SHA256SUMS.txt)",
    )
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_dir():
        print(f"FAIL not a directory: {directory}")
        return 1

    suffixes = {".msi", ".exe", ".msix", ".msixbundle"}
    files = sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in suffixes and p.name != "SHA256SUMS.txt"
    )
    if not files:
        print(f"FAIL no installer artifacts in {directory}")
        return 1

    out = args.output.resolve() if args.output else directory / "SHA256SUMS.txt"
    lines = [f"{sha256_file(path)}  {path.name}" for path in files]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS wrote {len(lines)} checksum(s) -> {out}")
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
