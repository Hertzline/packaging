# Linux packaging (HZ-050)

Public v1 Linux artifacts are **AppImage**, **Debian (.deb)**, **RPM**, plus a **Flatpak** manifest (Flathub) and an **AUR** draft. Formats and costs were decided in D5 (`spikes/D5.md`): all Linux channels are **$0**; Flathub / AUR publish remain owner-gated.

Official sources re-checked for this task (2026-11-15):

| Topic | URL |
|---|---|
| Tauri distribute overview | https://v2.tauri.app/distribute/ |
| Tauri AppImage | https://v2.tauri.app/distribute/appimage/ |
| Tauri Debian | https://v2.tauri.app/distribute/debian/ |
| Tauri RPM | https://v2.tauri.app/distribute/rpm/ |
| Tauri Flatpak / Flathub | https://v2.tauri.app/distribute/flatpak/ |
| Tauri AUR | https://v2.tauri.app/distribute/aur/ |
| DebConfig / RpmConfig | https://v2.tauri.app/reference/config/#debconfig |
| Flathub submission | https://docs.flathub.org/docs/for-app-authors/submission |
| D5 cost / format decision | `spikes/D5.md` |

Tauri CLI pin (sibling `app`): `@tauri-apps/cli` **2.12.4**. Bundle targets used: `appimage`, `deb`, `rpm` (Snap is out of v1 scope; D5 did not choose Snap).

## Layout

| Path | Role |
|---|---|
| `prerm-restore.sh` | AC-7.3: calls `hertzline-helper restore_all --reason uninstall` before remove |
| `tauri.linux.bundle.json` | Merge config for `tauri build` (AppImage + deb + rpm, prerm hooks, polkit file) |
| `flatpak/org.hertzline.Hertzline.yml` | Flatpak manifest wrapping the `.deb` (deb-based path from Tauri docs) |
| `flatpak/org.hertzline.Hertzline.metainfo.xml` | AppStream metainfo draft |
| `aur/PKGBUILD` | AUR draft extracting the release `.deb` |
| `aur/hertzline.install` | AUR install hooks (icons + restore on remove) |
| `aur/AUR.md` | Draft rules; no publish without owner approval |
| `SANDBOX.md` | Flatpak sandbox vs host helper / polkit limits |

## Sandbox and helper (required HZ-050 check)

| Channel | Helper / elevation | Limit |
|---|---|---|
| AppImage | Host process + host polkit | Full D2 path when `hertzline-helper` and `org.hertzline.helper.policy` are installed on the host |
| deb / rpm | Packages install helper + polkit policy under `/usr` | Full D2 path (`pkexec` / named polkit actions) |
| Flatpak | Sandbox cannot freely talk to host polkit | Prefer a **host-installed helper**, or label privileged actions **not-possible** inside Flatpak (see `SANDBOX.md`) |
| AUR | Same as deb contents after extract | Full D2 path |

Never claim Flatpak has full privileged apply/restore without a documented host-helper path.

## Build (Linux host)

From the `packaging` repo root on Linux (Ubuntu 22.04 / Debian 12 baseline per Tauri docs):

```text
python scripts/build_linux.py
```

The script:

1. Resolves sibling `../app` and optional `../helper` release binary (`hertzline-helper`).
2. Stages helper + polkit policy for the merge config `files` map.
3. Runs `npx tauri build --bundles appimage,deb,rpm --ci -c <packaging>/linux/tauri.linux.bundle.json` in `app`.
4. Copies artifacts into `packaging/dist/linux/<version>/`.
5. Writes SHA-256 checksums via `scripts/checksums.py`.

Dry-run (docs + script gates only, no Tauri compile):

```text
python scripts/build_linux.py --check-only
```

Windows hosts cannot produce Linux bundles with the stock Tauri toolchain; `--check-only` is the supported gate there. Full artifact builds belong on Linux CI or a Linux machine.

## Uninstall restore (AC-7.3)

deb and rpm must run restore **before** deleting files via Tauri `preRemoveScript` pointing at `prerm-restore.sh`:

```text
hertzline-helper restore_all --reason uninstall --json
```

AUR `pre_remove` in `hertzline.install` invokes the same helper when present. AppImage has no package manager prerm; users who used privileged actions should run restore-all from the app or helper before deleting the AppImage. Flatpak uninstall cannot drive host polkit restore; document host helper or not-possible (`SANDBOX.md`).

## Signing (GPG)

Public deb/rpm releases should be GPG-signed when a key is available. See `scripts/sign_linux.py`. Owner supplies key material. Agent never commits private keys.

```text
python scripts/sign_linux.py --public --artifacts dist/linux/<version>
```

Without credentials, `--public` exits non-zero (fail closed). AppImage checksums still ship via `SHA256SUMS.txt`; Flatpak / AUR publish stay owner-gated.

## Checksums

```text
python scripts/checksums.py dist/linux/<version>
```

Writes `SHA256SUMS.txt` next to AppImage / deb / rpm artifacts.

## Flatpak and AUR publish

Drafts only. Do **not** open a Flathub PR or push to `aur.archlinux.org` without explicit owner approval (`RULES.md`).
