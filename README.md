<div align="center">

<a href="https://github.com/Hertzline/packaging"><img src="https://capsule-render.vercel.app/api?type=waving&height=160&color=0:0f1412,55:12352c,100:0f6b4c&text=packaging&fontColor=e8eeeb&fontSize=52&fontAlignY=48&animation=twinkling" alt="Hertzline packaging" width="100%" /></a>

<img src="https://readme-typing-svg.demolab.com?font=IBM+Plex+Mono&weight=500&size=15&color=2A9B7A&center=true&vCenter=true&width=560&height=32&duration=2600&pause=1200&lines=Installers+%2B+checksums+%2B+signing+orchestration;winget+Hertzline.Hertzline;Never+skip+signing+for+public+releases" alt="Packaging" />

</div>

<br/>

<img src="https://capsule-render.vercel.app/api?type=rect&height=3&color=0:0f1412,35:2a9b7a,70:c9a227,100:0f1412" width="100%" alt="" />

<br/>

Installers, manifests, release scripts, checksums, and signing orchestration for [Hertzline](https://github.com/Hertzline).

Owner supplies certificates and approves purchases. Agents never purchase certs or submit to stores without explicit owner approval.

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
| `winget/` | HZ-053 draft manifests for `Hertzline.Hertzline` (no PR without approval) |
| `winget/WINGET.md` | Schema 1.12.0 notes, refresh steps, owner gate for HZ-054 |
| `release/RELEASE_FEED.md` | HZ-052 packaging -> `website` releases.json hook |
| `release/HZ059_RC.md` | HZ-059 v1.0.0 RC runbook (owner signing/publish gates) |
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

## winget manifests (HZ-053)

Draft multi-file manifests live under `winget/manifests/h/Hertzline/Hertzline/<version>/` (`ManifestVersion` **1.12.0**). Install string matches website/docs: `winget install Hertzline.Hertzline`.

```bash
python scripts/check_hz053.py
winget validate --manifest winget/manifests/h/Hertzline/Hertzline/0.0.0
```

Do **not** open a PR to `microsoft/winget-pkgs` without explicit owner approval (HZ-054). See `winget/WINGET.md`.

## v1 release candidate (HZ-059)

See `release/HZ059_RC.md`. Summary:

```bash
# After app version is 1.0.0 and Windows artifacts exist:
python scripts/build_windows.py
python scripts/prepare_rc_winget.py
python scripts/sign_windows.py --public --artifacts dist/windows/1.0.0
python scripts/check_hz059.py
winget validate --manifest winget/manifests/h/Hertzline/Hertzline/1.0.0
```

Keep website `releases.json` at `not_released` until signed public HTTPS assets exist. Agents never deploy Vercel or open winget-pkgs PRs.

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
python scripts/check_hz053.py
python scripts/check_hz059.py
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
