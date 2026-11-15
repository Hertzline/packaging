# macOS Developer ID signing and notarization (HZ-051)

Public macOS DMG artifacts must be **Developer ID signed and notarized**. **Never skip signing silently.** Release scripts fail closed when credentials are missing.

Official guide: [macOS Code Signing | Tauri](https://v2.tauri.app/distribute/sign/macos/) (re-fetched 2026-11-15). Costs: Apple Developer Program **$99/yr** (`spikes/D5.md`). Purchases are owner-gated (`RULES.md`).

## Chosen path (v1)

| Step | Requirement |
|---|---|
| Membership | Apple Developer Program ($99/yr) |
| Certificate | **Developer ID Application** (outside Mac App Store) |
| Notarization | Required when using Developer ID Application |
| Stapling | Default after notarization (Tauri staples unless `--skip-stapling`) |

Do **not** use ad-hoc identity `-` for public releases. Free Apple Developer accounts cannot notarize (Tauri docs); Gatekeeper will still warn.

## Environment (public release)

`scripts/sign_macos.py --public` fails unless credentials are present.

### Signing (at least one)

| Mode | Required |
|---|---|
| Keychain identity (local Mac) | `APPLE_SIGNING_IDENTITY` (from `security find-identity -v -p codesigning`) |
| CI imported `.p12` | `APPLE_CERTIFICATE` (base64 `.p12`) + `APPLE_CERTIFICATE_PASSWORD` + `APPLE_SIGNING_IDENTITY` |

### Notarization (at least one complete set)

| Mode | Required |
|---|---|
| App Store Connect API | `APPLE_API_ISSUER`, `APPLE_API_KEY`, `APPLE_API_KEY_PATH` |
| Apple ID | `APPLE_ID`, `APPLE_PASSWORD` (app-specific), `APPLE_TEAM_ID` |

Never commit private keys, `.p12` / `.cer` files, API key `.p8` files, or app-specific passwords.

## Local unsigned / ad-hoc builds

Allowed for developer iteration only (especially Apple Silicon, where some form of signature is needed to launch):

```text
python scripts/build_macos.py
# omit --public-sign
```

Artifacts under `dist/macos/` from an unsigned or ad-hoc build must not be published to GitHub Releases or `/download/`.

## Verify after notarization

On a Mac with the signed app / DMG:

```text
codesign --verify --deep --strict --verbose=2 /path/to/Hertzline.app
spctl --assess --type execute -v /path/to/Hertzline.app
xcrun stapler validate /path/to/Hertzline_x.y.z.dmg
```

Record tool versions and machine OS in `PROGRESS.md` when a real notarized build exists. Until the owner enrolls and supplies certs, signing/notarization checks are **unavailable** (owner-gated), not silently skipped.
