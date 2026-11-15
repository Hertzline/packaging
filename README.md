# Hertzline / packaging

Installers, manifests, release scripts, checksums, and signing orchestration for [Hertzline](https://github.com/Hertzline).

Owner supplies certificates and approves purchases. Agents never purchase certs, submit to stores, or open winget PRs without explicit owner approval.

## Layout

| Path | Role |
|---|---|
| `spikes/D5.md` | HZ-008 packaging + signing costs decision |
| `spikes/D6.md` | HZ-009 auto-update + signature verification decision |
| `windows/WINDOWS.md` | HZ-049 MSI + NSIS build, checksums, uninstall restore |
| `windows/SIGNING.md` | Authenticode / Artifact Signing; fail closed |
| `windows/MSIX.md` | Optional Store MSIX (not Tauri-native) |
| `windows/uninstall-restore.ps1` | AC-7.3 uninstall invokes `hertzline-helper restore_all` |
| `windows/nsis-hooks.nsh` | NSIS `PREUNINSTALL` restore hook |
| `windows/wix/uninstall-restore.wxs` | MSI CustomAction before `RemoveFiles` |
| `linux/prerm-restore.sh` | HZ-018 / HZ-050 deb/rpm prerm restore hook |
| `linux/LINUX.md` | HZ-050 AppImage + deb + rpm + Flatpak + AUR |
| `linux/SANDBOX.md` | Flatpak sandbox vs host polkit/helper limits |
| `linux/flatpak/` | Flatpak manifest + AppStream metainfo draft |
| `linux/aur/` | AUR PKGBUILD draft (no publish without approval) |
| `macos/uninstall-restore.sh` | HZ-018 uninstall restore before SMAppService unregister |
| `macos/MACOS.md` | HZ-051 DMG build, notarization steps + costs |
| `macos/SIGNING.md` | Developer ID + notarization; fail closed |
| `macos/homebrew/` | Homebrew cask draft (no publish without approval) |
| `winget/` | Manifests for `Hertzline.Hertzline` (authored later) |
| `release/RELEASE_FEED.md` | HZ-052 packaging -> `website` releases.json hook |
| `fixtures/hz052/` | Sample SHA256SUMS for the release-feed gate |
| `scripts/` | Build, checksum, sign, and gate helpers |

## Decision (D5)

See `spikes/D5.md`. Summary:

- Windows: MSI + NSIS for direct download and winget; MSIX optional for Store later.
- Linux: Flatpak (Flathub), AppImage, deb, rpm, AUR.
- macOS: signed + notarized `.dmg` + Homebrew cask draft.
- Signing required for public Windows/macOS releases; never skip silently.
- Purchases and store/winget submissions are owner-gated.

## Decision (D6)

See `spikes/D6.md`. Summary:

- Direct downloads: Tauri updater with mandatory minisign verify + `requireSignedVersion`.
- Channel installs: winget / Flatpak / Homebrew own updates; in-app updater off.
- Manual download + SHA-256 always available.
- Never signature-optional or silent unsigned updates.

## Windows build (HZ-049)

Requires sibling `../app` on a Windows host (WiX for MSI). See `windows/WINDOWS.md`.

```bash
python scripts/build_windows.py --check-only
python scripts/build_windows.py
python scripts/sign_windows.py --public --artifacts dist/windows/<version>
python scripts/build_msix.py
```

Public signing fails closed without owner-supplied credentials (`windows/SIGNING.md`).

## Linux build (HZ-050)

Requires sibling `../app` on a **Linux** host (WebKitGTK 4.1; Ubuntu 22.04 / Debian 12 baseline). See `linux/LINUX.md` and `linux/SANDBOX.md`.

```bash
python scripts/build_linux.py --check-only
python scripts/build_linux.py
python scripts/sign_linux.py --public --artifacts dist/linux/<version>
```

Flatpak and AUR drafts are under `linux/flatpak/` and `linux/aur/`. Do not submit to Flathub or the AUR without owner approval.

Public GPG signing fails closed without owner-supplied key (`scripts/sign_linux.py --public`).

## macOS build (HZ-051)

Requires sibling `../app` on a **macOS** host (Xcode CLT). See `macos/MACOS.md` and `macos/SIGNING.md`.

```bash
python scripts/build_macos.py --check-only
python scripts/build_macos.py
python scripts/sign_macos.py --public --artifacts dist/macos/<version>
```

Homebrew cask draft is under `macos/homebrew/`. Do not open a homebrew-cask PR without owner approval.

Public Developer ID + notarization fails closed without owner-supplied Apple Program credentials (`macos/SIGNING.md`). Cost: **$99/yr** Apple Developer Program (D5).

## Release metadata -> website (HZ-052)

After signed artifacts exist, generate the static download/changelog feed (no secrets):

```bash
python scripts/write_release_metadata.py --help
python scripts/check_hz052.py
```

See `release/RELEASE_FEED.md`. Output targets sibling `../website/src/data/releases.json`. Owner deploys Vercel; agents never deploy.

## Checks

```bash
# From repo root (PowerShell or bash)
python scripts/check_d5.py
python scripts/check_d6.py
python scripts/check_hz018.py
python scripts/check_hz049.py
python scripts/check_hz050.py
python scripts/check_hz051.py
python scripts/check_hz052.py
```

### Uninstall restore (HZ-018 / HZ-049 / HZ-050 / HZ-051 / AC-7.3)

Before deleting binaries, installers must run the OS restore hook so outstanding Hertzline changes are reverted without the UI:

```text
hertzline-helper restore_all --reason uninstall --json
```

Optional store override: `--store PATH` or `HERTZLINE_SNAPSHOT_STORE`.

## License

[MIT](LICENSE)

Third-party notices: [NOTICE](NOTICE)
