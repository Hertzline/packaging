# Hertzline / packaging

Installers, manifests, release scripts, checksums, and signing orchestration for [Hertzline](https://github.com/Hertzline).

Owner supplies certificates and approves purchases. Agents never purchase certs, submit to stores, or open winget PRs without explicit owner approval.

## Layout

| Path | Role |
|---|---|
| `spikes/D5.md` | HZ-008 packaging + signing costs decision |
| `spikes/D6.md` | HZ-009 auto-update + signature verification decision |
| `windows/` | MSI / NSIS / MSIX notes and future scripts |
| `linux/` | Flatpak / AppImage / deb / rpm / AUR notes |
| `macos/` | dmg / notarization / Homebrew cask notes |
| `winget/` | Manifests for `Hertzline.Hertzline` (authored later) |
| `scripts/` | Checksum and release helpers (later tasks) |

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

## Checks

```bash
# From repo root (PowerShell or bash)
python scripts/check_d5.py
python scripts/check_d6.py
```

## License

[MIT](LICENSE)

Third-party notices: [NOTICE](NOTICE)
