# macOS packaging (HZ-051)

Public v1 macOS artifact is a **Developer ID signed + notarized `.dmg`**, plus a **Homebrew cask draft**. Formats and costs were decided in D5 (`spikes/D5.md`): Apple Developer Program **$99/yr**; notarization included; Homebrew cask publish remains owner-gated.

Official sources re-checked for this task (2026-11-15):

| Topic | URL |
|---|---|
| Tauri DMG | https://v2.tauri.app/distribute/dmg/ |
| Tauri macOS app bundle | https://v2.tauri.app/distribute/macos-application-bundle/ |
| Tauri macOS code signing + notarization | https://v2.tauri.app/distribute/sign/macos/ |
| Apple notarization | https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution |
| Apple Developer Program enrollment / fee | https://developer.apple.com/help/account/membership/program-enrollment/ |
| Homebrew Cask Cookbook | https://docs.brew.sh/Cask-Cookbook |
| D5 cost / format decision | `spikes/D5.md` |

Tauri CLI pin (sibling `app`): `@tauri-apps/cli` **2.12.4**. Bundle target used: `dmg` (also produces the `.app` bundle). Mac App Store path is out of v1 direct-download scope (D5).

## Costs (owner-gated; no purchase by agent)

| Item | Cost | Notes |
|---|---|---|
| Apple Developer Program | **$99 USD / year** (local currency where offered) | Required for Developer ID Application cert + notarization |
| Apple Developer Enterprise Program | **$299 USD / year** | Not chosen for Hertzline v1 |
| Notarization service | Included in Program | Required for Gatekeeper-friendly outside-App-Store DMG |
| Homebrew cask draft / PR | **$0** | Do not open a homebrew-cask PR without owner approval |

## Layout

| Path | Role |
|---|---|
| `uninstall-restore.sh` | AC-7.3: calls `hertzline-helper restore_all --reason uninstall` before remove / SMAppService unregister |
| `tauri.macos.bundle.json` | Merge config for `tauri build --bundles dmg` (min macOS 13 for SMAppService) |
| `SIGNING.md` | Developer ID + notarization env; fail closed |
| `homebrew/hertzline.rb` | Homebrew cask draft (PLACEHOLDER checksums) |
| `homebrew/CASK.md` | Draft rules; no publish without owner approval |

## Helper and privilege (D2)

| Channel | Helper / elevation | Limit |
|---|---|---|
| Notarized DMG | Host-installed / co-located `hertzline-helper` via SMAppService LaunchDaemon (macOS 13+) | Register on first privileged need; unregister on uninstall after restore |
| Homebrew cask | Same as DMG contents after install | Same D2 path |

Minimum system version in the merge config is **13.0** (Ventura) because D2 chose `SMAppService` (macOS 13+). Do not claim privileged actions work on older macOS.

## Build (macOS host)

From the `packaging` repo root on a Mac with Xcode CLT:

```text
python scripts/build_macos.py
```

The script:

1. Resolves sibling `../app` and optional `../helper` release binary (`hertzline-helper`).
2. Stages helper + uninstall restore script for the merge config.
3. Runs `npx tauri build --bundles dmg --ci -c <packaging>/macos/tauri.macos.bundle.json` in `app`.
4. Copies `.dmg` artifacts into `packaging/dist/macos/<version>/`.
5. Writes SHA-256 checksums via `scripts/checksums.py`.

Dry-run (docs + script gates only, no Tauri compile):

```text
python scripts/build_macos.py --check-only
```

Windows and Linux hosts cannot produce Apple Disk Images with the stock Tauri toolchain; `--check-only` is the supported gate there. Full artifact builds belong on macOS CI or a Mac.

## Notarization steps (owner)

See `SIGNING.md` for env vars. Summary from Tauri macOS signing docs:

1. Enroll in Apple Developer Program ($99/yr) -- owner purchase.
2. Create a **Developer ID Application** certificate (Account Holder); install in Keychain or export for CI.
3. Set signing identity (`APPLE_SIGNING_IDENTITY` or `bundle.macOS.signingIdentity`).
4. Provide notarization credentials (App Store Connect API key **or** Apple ID + app-specific password + Team ID).
5. Rebuild: `tauri build --bundles dmg` notarizes when credentials are present.
6. Staple is the default; use `--skip-stapling` only for an initial notarization pass if needed.
7. Verify Gatekeeper: `spctl --assess --type execute -v /path/to/Hertzline.app` and open the DMG on a clean Mac.

Never ship an unsigned or un-notarized public DMG. Ad-hoc signing (`signingIdentity: "-"`) is for local ARM testing only; it is not a public release path.

## Uninstall restore (AC-7.3)

Before deleting the app or unregistering SMAppService, run:

```text
hertzline-helper restore_all --reason uninstall --json
```

`uninstall-restore.sh` wraps that call. The DMG drag-to-Applications install has no package prerm; document that users who applied privileged actions should restore-all from the app or helper before deleting `Hertzline.app`. Homebrew `zap` does not replace restore-all; see `homebrew/CASK.md`.

## Checksums

```text
python scripts/checksums.py dist/macos/<version>
```

Writes `SHA256SUMS.txt` next to `.dmg` artifacts.

## Homebrew cask publish

Draft only under `macos/homebrew/`. Do **not** open a PR to `Homebrew/homebrew-cask` without explicit owner approval (`RULES.md`).
