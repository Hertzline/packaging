# Homebrew cask draft (HZ-051)

| Item | Value |
|---|---|
| Proposed cask token | `hertzline` |
| Source | Notarized `.dmg` from `Hertzline/app` GitHub Releases |
| License | MIT |
| Depends | macOS 13+ (Ventura; SMAppService helper) |

## Status

Draft only. File: `hertzline.rb`.

## Owner gate

Per `RULES.md` / D5: do **not** open a PR to `Homebrew/homebrew-cask`, tap, or publish without explicit owner approval.

Before publish:

1. Replace `version` and `sha256` with real notarized release values (never ship PLACEHOLDER).
2. Confirm the DMG URL matches the GitHub Release asset name from `scripts/build_macos.py`.
3. Test `brew install --cask ./hertzline.rb` then uninstall; run restore-all (AC-7.3) before deleting the app if privileged actions were used.
4. `zap` trash paths are best-effort cleanup; they do **not** replace `hertzline-helper restore_all --reason uninstall`.
