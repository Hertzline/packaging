#!/usr/bin/env python3
"""HZ-052 local check: release metadata -> website feed hook."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts" / "write_release_metadata.py"
FIXTURES = ROOT / "fixtures" / "hz052"
DOC = ROOT / "release" / "RELEASE_FEED.md"

REQUIRED_FILES = [
    WRITER,
    DOC,
    FIXTURES / "windows" / "SHA256SUMS.txt",
    FIXTURES / "linux" / "SHA256SUMS.txt",
    FIXTURES / "macos" / "SHA256SUMS.txt",
]

DOC_MARKERS = [
    "write_release_metadata.py",
    "releases.json",
    "SHA-256",
    "https://",
    "not_released",
    "secret",
    "Vercel",
]


def run_writer(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(WRITER), *args],
        capture_output=True,
        text=True,
    )


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.is_file()]
    if missing:
        print("FAIL missing files:", ", ".join(missing))
        return 1

    doc = DOC.read_text(encoding="utf-8")
    absent = [m for m in DOC_MARKERS if m.lower() not in doc.lower()]
    if absent:
        print("FAIL RELEASE_FEED.md missing markers:", ", ".join(absent))
        return 1
    print("PASS release/RELEASE_FEED.md markers")

    base = "https://github.com/Hertzline/app/releases/download/v0.1.0"
    with tempfile.TemporaryDirectory(prefix="hz052-") as tmp:
        tmp_path = Path(tmp)
        out_released = tmp_path / "releases.released.json"
        released = run_writer(
            [
                "--version",
                "0.1.0",
                "--published",
                "2026-11-15",
                "--status",
                "released",
                "--base-url",
                base,
                "--windows-sums",
                str(FIXTURES / "windows" / "SHA256SUMS.txt"),
                "--linux-sums",
                str(FIXTURES / "linux" / "SHA256SUMS.txt"),
                "--macos-sums",
                str(FIXTURES / "macos" / "SHA256SUMS.txt"),
                "--highlight-en",
                "Fixture release for HZ-052 gate",
                "--highlight-it",
                "Release di fixture per il gate HZ-052",
                "--size",
                "Hertzline_0.1.0_x64_en-US.msi=2244608",
                "-o",
                str(out_released),
            ]
        )
        if released.returncode != 0:
            print("FAIL writer released path")
            print(released.stdout, released.stderr)
            return 1
        data = json.loads(out_released.read_text(encoding="utf-8"))
        if data.get("status") != "released":
            print("FAIL expected status=released")
            return 1
        latest = data.get("latest") or {}
        if latest.get("version") != "0.1.0" or latest.get("published") != "2026-11-15":
            print("FAIL latest version/published mismatch")
            return 1
        if "minOs" not in latest:
            print("FAIL latest.minOs missing")
            return 1
        arts = data.get("artifacts") or {}
        counts = {k: len(arts.get(k) or []) for k in ("windows", "linux", "macos")}
        if counts != {"windows": 2, "linux": 3, "macos": 1}:
            print(f"FAIL artifact counts {counts}")
            return 1
        for os_key, rows in arts.items():
            for row in rows:
                for key in ("id", "label", "url", "sha256"):
                    if not row.get(key):
                        print(f"FAIL artifact missing {key} under {os_key}")
                        return 1
                if not str(row["url"]).startswith("https://"):
                    print("FAIL non-https artifact url")
                    return 1
                if len(row["sha256"]) != 64:
                    print("FAIL sha256 length")
                    return 1
        history = data.get("history") or []
        if not history or history[0].get("version") != "0.1.0":
            print("FAIL history missing version entry")
            return 1
        blob = out_released.read_text(encoding="utf-8")
        for banned in ("PRIVATE KEY", "ghp_", "CSC_KEY_PASSWORD", "APPLE_ID_PASSWORD"):
            if banned in blob:
                print(f"FAIL secret-like token leaked: {banned}")
                return 1
        print(
            f"PASS writer released artifacts={sum(counts.values())} "
            f"history={len(history)} secrets=0"
        )

        out_clear = tmp_path / "releases.clear.json"
        cleared = run_writer(
            [
                "--version",
                "0.1.0",
                "--published",
                "2026-11-15",
                "--status",
                "not_released",
                "--base-url",
                base,
                "--windows-sums",
                str(FIXTURES / "windows" / "SHA256SUMS.txt"),
                "--template",
                str(out_released),
                "-o",
                str(out_clear),
            ]
        )
        if cleared.returncode != 0:
            print("FAIL writer not_released path")
            print(cleared.stdout, cleared.stderr)
            return 1
        clear_data = json.loads(out_clear.read_text(encoding="utf-8"))
        if clear_data.get("status") != "not_released":
            print("FAIL expected not_released")
            return 1
        if clear_data.get("latest") is not None:
            print("FAIL not_released must null latest")
            return 1
        for os_key in ("windows", "linux", "macos"):
            if clear_data.get("artifacts", {}).get(os_key) != []:
                print(f"FAIL not_released artifacts.{os_key} must be []")
                return 1
        if clear_data.get("history") != []:
            print("FAIL not_released history must be []")
            return 1
        if clear_data.get("wingetPublished") is not False:
            print("FAIL not_released wingetPublished must be false")
            return 1
        print("PASS writer not_released clears artifacts/history")

        secret_sums = tmp_path / "SHA256SUMS.secret.txt"
        secret_sums.write_text(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  "
            "Hertzline_0.1.0_x64_en-US.msi\n"
            "BEGIN RSA PRIVATE KEY\n",
            encoding="utf-8",
        )
        secret = run_writer(
            [
                "--version",
                "0.1.0",
                "--published",
                "2026-11-15",
                "--status",
                "released",
                "--base-url",
                base,
                "--windows-sums",
                str(secret_sums),
                "-o",
                str(tmp_path / "should-not-exist.json"),
            ]
        )
        if secret.returncode == 0:
            print("FAIL writer must reject secret-like sums content")
            return 1
        print("PASS writer rejects secret-like checksum input")

        http = run_writer(
            [
                "--version",
                "0.1.0",
                "--published",
                "2026-11-15",
                "--status",
                "released",
                "--base-url",
                "http://example.invalid/v0.1.0",
                "--windows-sums",
                str(FIXTURES / "windows" / "SHA256SUMS.txt"),
                "-o",
                str(tmp_path / "http.json"),
            ]
        )
        if http.returncode == 0:
            print("FAIL writer must require https base-url")
            return 1
        print("PASS writer rejects non-https base-url")

    print("PASS hz052_release_metadata_hook ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
