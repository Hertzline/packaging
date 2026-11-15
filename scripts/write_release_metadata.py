#!/usr/bin/env python3
"""HZ-052: build website release feed from packaging checksums + public URLs.

Writes version, published date, per-OS artifact URLs, and SHA-256 into a
releases.json document matching website/src/data/releases.json. Never embeds
secrets, private keys, or signing material.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY", re.I),
    re.compile(r"BEGIN\s+OPENSSH\s+PRIVATE\s+KEY", re.I),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN\s+CERTIFICATE-----"),
    re.compile(r"minisign\s+secret", re.I),
    re.compile(r"APPLE_ID_PASSWORD", re.I),
    re.compile(r"CSC_KEY_PASSWORD", re.I),
]

OS_SUFFIX = {
    ".msi": ("windows", "windows-msi", "Windows MSI"),
    ".exe": ("windows", "windows-nsis", "Windows NSIS setup"),
    ".msix": ("windows", "windows-msix", "Windows MSIX"),
    ".msixbundle": ("windows", "windows-msixbundle", "Windows MSIX bundle"),
    ".deb": ("linux", "linux-deb", "Linux .deb"),
    ".rpm": ("linux", "linux-rpm", "Linux .rpm"),
    ".appimage": ("linux", "linux-appimage", "Linux AppImage"),
    ".dmg": ("macos", "macos-dmg", "macOS DMG"),
}

DEFAULT_MIN_OS = {
    "windows": "Windows 10 (64-bit)",
    "linux": "x86_64 (Ubuntu 22.04 / Debian 12 baseline)",
    "macos": "macOS 13.0 (Ventura)",
}


def fail(msg: str) -> int:
    print(f"FAIL {msg}")
    return 1


def reject_secrets(blob: str, where: str) -> str | None:
    for pat in SECRET_PATTERNS:
        if pat.search(blob):
            return f"secret-like pattern in {where}: {pat.pattern}"
    return None


def parse_sha256sums(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    bad = reject_secrets(text, str(path))
    if bad:
        raise ValueError(bad)
    rows: list[tuple[str, str]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # GNU coreutils: "<hex>  <name>" or "<hex> *<name>"
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(\S.+)", line)
        if not match:
            raise ValueError(f"{path}:{line_no}: expected '<sha256>  <filename>'")
        digest, name = match.group(1).lower(), match.group(2).strip()
        if not name or "/" in name or "\\" in name:
            raise ValueError(f"{path}:{line_no}: filename must be basename only")
        rows.append((digest, name))
    if not rows:
        raise ValueError(f"{path}: no checksum rows")
    return rows


def classify(filename: str) -> tuple[str, str, str]:
    lower = filename.lower()
    if lower.endswith(".appimage"):
        return OS_SUFFIX[".appimage"]
    suffix = Path(lower).suffix
    if suffix not in OS_SUFFIX:
        raise ValueError(f"unsupported artifact suffix for {filename}")
    return OS_SUFFIX[suffix]


def artifact_entry(
    filename: str,
    sha256: str,
    base_url: str,
    size_bytes: int | None,
) -> tuple[str, dict[str, Any]]:
    os_key, art_id, label_prefix = classify(filename)
    url = f"{base_url.rstrip('/')}/{filename}"
    if not url.startswith("https://"):
        raise ValueError(f"artifact URL must be https: {url}")
    entry: dict[str, Any] = {
        "id": art_id,
        "label": f"{label_prefix} ({filename})",
        "url": url,
        "sha256": sha256,
        "filename": filename,
    }
    if size_bytes is not None:
        entry["sizeBytes"] = size_bytes
    return os_key, entry


def load_template(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "status": "not_released",
            "updated": "",
            "wingetId": "Hertzline.Hertzline",
            "wingetCommand": "winget install Hertzline.Hertzline",
            "wingetPublished": False,
            "product": {
                "name": "Hertzline",
                "license": "MIT",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystems": ["Windows", "Linux", "macOS"],
                "description": {
                    "en": "Measure, explain, and reverse game and desktop performance changes. No unverified FPS claims.",
                    "it": "Misura, spiega e annulla le modifiche alle prestazioni di giochi e desktop. Nessun claim di FPS non verificato.",
                },
            },
            "requirements": {
                "windows": {
                    "en": "Windows 10 or newer (64-bit). Signed MSI/NSIS installers planned. Elevation only when an action needs it.",
                    "it": "Windows 10 o successivo (64-bit). Installer MSI/NSIS firmati previsti. Elevazione solo quando un'azione la richiede.",
                },
                "linux": {
                    "en": "x86_64. Flatpak, AppImage, .deb, .rpm, and AUR packages planned. Privileged actions use polkit where required.",
                    "it": "x86_64. Pacchetti Flatpak, AppImage, .deb, .rpm e AUR previsti. Le azioni privilegiate usano polkit dove richiesto.",
                },
                "macos": {
                    "en": "macOS 13 or newer. Notarized DMG and Homebrew cask planned. Fewer tunables than Windows/Linux; capability surface is honest.",
                    "it": "macOS 13 o successivo. DMG notarizzato e cask Homebrew previsti. Meno regolazioni di Windows/Linux; la superficie di capacita e dichiarata onestamente.",
                },
            },
            "latest": None,
            "artifacts": {"windows": [], "linux": [], "macos": []},
            "history": [],
            "ui": {},
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("template must be a JSON object")
    bad = reject_secrets(json.dumps(data), str(path))
    if bad:
        raise ValueError(bad)
    return data


def build_feed(
    *,
    template: dict[str, Any],
    version: str,
    published: str,
    status: str,
    base_url: str,
    sums_by_os: dict[str, Path],
    size_lookup: dict[str, int],
    highlights_en: list[str],
    highlights_it: list[str],
    winget_published: bool,
) -> dict[str, Any]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("version must be MAJOR.MINOR.PATCH (no leading v)")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
        raise ValueError("published must be YYYY-MM-DD")
    if status not in ("not_released", "released"):
        raise ValueError("status must be not_released or released")
    if not base_url.startswith("https://"):
        raise ValueError("base-url must be https")

    artifacts: dict[str, list[dict[str, Any]]] = {
        "windows": [],
        "linux": [],
        "macos": [],
    }
    for os_key, sums_path in sums_by_os.items():
        for digest, filename in parse_sha256sums(sums_path):
            classified_os, entry = artifact_entry(
                filename,
                digest,
                f"{base_url.rstrip('/')}/{os_key}",
                size_lookup.get(filename),
            )
            if classified_os != os_key:
                raise ValueError(
                    f"{filename} classified as {classified_os} but listed under {os_key}"
                )
            artifacts[os_key].append(entry)

    out = dict(template)
    out["status"] = status
    out["updated"] = published
    out["wingetId"] = "Hertzline.Hertzline"
    out["wingetCommand"] = "winget install Hertzline.Hertzline"
    out["wingetPublished"] = bool(winget_published)

    if status == "not_released":
        out["latest"] = None
        out["artifacts"] = {"windows": [], "linux": [], "macos": []}
        out["history"] = []
        out["wingetPublished"] = False
    else:
        total = sum(len(v) for v in artifacts.values())
        if total == 0:
            raise ValueError("released status requires at least one artifact")
        for os_key, rows in artifacts.items():
            for row in rows:
                if not row.get("sha256") or not row.get("url"):
                    raise ValueError(f"incomplete artifact under {os_key}")
        out["artifacts"] = artifacts
        latest = {
            "version": version,
            "published": published,
            "tag": f"v{version}",
            "minOs": dict(DEFAULT_MIN_OS),
            "downloadPath": "/download/",
        }
        out["latest"] = latest
        history = list(out.get("history") or [])
        history = [h for h in history if h.get("version") != version]
        history.insert(
            0,
            {
                "version": version,
                "published": published,
                "tag": f"v{version}",
                "highlights": {"en": highlights_en, "it": highlights_it},
                "artifactCount": total,
            },
        )
        out["history"] = history

    blob = json.dumps(out, indent="\t", ensure_ascii=True) + "\n"
    bad = reject_secrets(blob, "output")
    if bad:
        raise ValueError(bad)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="MAJOR.MINOR.PATCH")
    parser.add_argument("--published", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--status",
        choices=("not_released", "released"),
        default="not_released",
        help="Feed status (default not_released keeps empty artifacts)",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="HTTPS base for artifacts, e.g. https://github.com/Hertzline/app/releases/download/v1.0.0",
    )
    parser.add_argument(
        "--windows-sums",
        type=Path,
        default=None,
        help="Path to Windows SHA256SUMS.txt",
    )
    parser.add_argument(
        "--linux-sums",
        type=Path,
        default=None,
        help="Path to Linux SHA256SUMS.txt",
    )
    parser.add_argument(
        "--macos-sums",
        type=Path,
        default=None,
        help="Path to macOS SHA256SUMS.txt",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Existing website releases.json to preserve ui/product/requirements",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output releases.json path (website/src/data/releases.json or staging)",
    )
    parser.add_argument(
        "--highlight-en",
        action="append",
        default=[],
        help="English changelog highlight (repeatable)",
    )
    parser.add_argument(
        "--highlight-it",
        action="append",
        default=[],
        help="Italian changelog highlight (repeatable)",
    )
    parser.add_argument(
        "--winget-published",
        action="store_true",
        help="Set wingetPublished true (owner-gated; never for not_released)",
    )
    parser.add_argument(
        "--size",
        action="append",
        default=[],
        metavar="NAME=BYTES",
        help="Optional sizeBytes for a filename",
    )
    args = parser.parse_args()

    size_lookup: dict[str, int] = {}
    for item in args.size:
        if "=" not in item:
            return fail(f"bad --size {item}")
        name, raw = item.split("=", 1)
        try:
            size_lookup[name] = int(raw)
        except ValueError:
            return fail(f"bad --size bytes for {name}")

    sums_by_os: dict[str, Path] = {}
    for os_key, path in (
        ("windows", args.windows_sums),
        ("linux", args.linux_sums),
        ("macos", args.macos_sums),
    ):
        if path is None:
            continue
        if not path.is_file():
            return fail(f"missing sums file: {path}")
        sums_by_os[os_key] = path.resolve()

    if args.status == "released" and not sums_by_os:
        return fail("released requires at least one --*-sums file")

    try:
        template = load_template(args.template.resolve() if args.template else None)
        feed = build_feed(
            template=template,
            version=args.version,
            published=args.published,
            status=args.status,
            base_url=args.base_url,
            sums_by_os=sums_by_os,
            size_lookup=size_lookup,
            highlights_en=list(args.highlight_en),
            highlights_it=list(args.highlight_it),
            winget_published=args.winget_published,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return fail(str(exc))

    out_path = args.output.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(feed, indent="\t", ensure_ascii=True) + "\n"
    out_path.write_text(text, encoding="utf-8")
    art_n = sum(len(feed["artifacts"][k]) for k in ("windows", "linux", "macos"))
    print(
        f"PASS wrote {out_path} status={feed['status']} "
        f"version={args.version} artifacts={art_n} secrets=0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
