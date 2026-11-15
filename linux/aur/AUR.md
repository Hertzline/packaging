# AUR package draft (HZ-050)

| Item | Value |
|---|---|
| Proposed package name | `hertzline` |
| Source | Release `.deb` from `Hertzline/app` GitHub Releases |
| License | MIT |
| Depends | Tauri GTK/WebKit set + `polkit` (helper elevation) |

## Status

Draft only. Files: `PKGBUILD`, `hertzline.install`.

## Owner gate

Per `RULES.md` / D5: do **not** create an AUR account push, publish, or update `aur.archlinux.org/hertzline` without explicit owner approval.

Before publish:

1. Replace `pkgver` and `sha256sums_x86_64` with real release values.
2. Run `makepkg --printsrcinfo > .SRCINFO` on Arch.
3. Test `makepkg` install + uninstall restore (AC-7.3).
