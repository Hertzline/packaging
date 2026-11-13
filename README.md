# Hertzline / packaging

Installers, manifests, release scripts, checksums, and signing orchestration for [Hertzline](https://github.com/Hertzline).

Owner supplies certificates and approves purchases. Agents never purchase certs, submit to stores, or open winget PRs without explicit owner approval.

## Layout

| Path | Role |
|---|---|
| `spikes/D5.md` | HZ-008 packaging + signing costs decision |
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

## Checks

```bash
# From repo root (PowerShell or bash)
python scripts/check_d5.py
```

## License

[MIT](LICENSE)

Third-party notices: [NOTICE](NOTICE)
