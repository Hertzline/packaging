# HZ-059 -- v1 release candidate

Version: **1.0.0** (app SemVer; git tag `v1.0.0` after signed publish)

This document is the RC runbook. Agents prepare builds, checksums, winget
drafts, and website feed hooks. Owners sign, notarize, publish GitHub
Release assets, deploy Vercel, and approve winget.

## Agent-complete checklist

1. App version files are `1.0.0` (`tauri.conf.json`, crate manifests, `package.json`).
2. `app/CHANGELOG.md` has a `[1.0.0]` section (source of truth).
3. Windows MSI + NSIS built into `dist/windows/1.0.0/` with `SHA256SUMS.txt`.
4. `python scripts/sign_windows.py --public --artifacts dist/windows/1.0.0` fail closed without owner certs.
5. Linux / macOS full bundles: build on those hosts (`build_linux.py` / `build_macos.py`); unavailable on Windows CI hosts is recorded honestly.
6. winget manifests under `winget/manifests/h/Hertzline/Hertzline/1.0.0/` validate locally (`winget validate`). No winget-pkgs PR (HZ-054).
7. Website `releases.json` stays `status: not_released` until **signed** public HTTPS artifacts exist (`RELEASE_FEED.md`).
8. `python scripts/check_hz059.py` PASS.

## Owner-only steps (do not skip signing)

1. Supply Windows Authenticode (Artifact Signing or OV) and run:

   ```bash
   python scripts/sign_windows.py --public --artifacts dist/windows/1.0.0
   ```

2. On Linux: build + GPG-sign (`sign_linux.py --public`).
3. On macOS: build + Developer ID + notarize (`sign_macos.py --public`). Cost: Apple Developer Program $99/yr (D5).
4. Publish signed assets to `Hertzline/app` GitHub Releases at tag `v1.0.0`.
5. Refresh SHA-256 / ProductCode in winget `1.0.0` manifests from the **signed** MSI.
6. Write website feed:

   ```bash
   python scripts/write_release_metadata.py \
     --version 1.0.0 \
     --published YYYY-MM-DD \
     --status released \
     --base-url https://github.com/Hertzline/app/releases/download/v1.0.0 \
     --windows-sums dist/windows/1.0.0/SHA256SUMS.txt \
     --linux-sums dist/linux/1.0.0/SHA256SUMS.txt \
     --macos-sums dist/macos/1.0.0/SHA256SUMS.txt \
     --template ../website/src/data/releases.json \
     --highlight-en "v1.0.0 measured release" \
     --highlight-it "Rilascio misurato v1.0.0" \
     -o ../website/src/data/releases.json
   ```

7. Owner deploys `website` on Vercel (agents never install or run the Vercel CLI).
8. Explicit chat approval required before any winget-pkgs PR (HZ-054).

## Forbidden

- Publishing unsigned binaries as a public "signed" release
- Setting `releases.json` to `released` without live HTTPS signed artifacts
- winget-pkgs / Flathub / AUR / Homebrew PRs without owner approval
- Vercel CLI, login, link, env, or deploy by the agent
