# Windows packaging (HZ-049)

Public v1 artifacts are **MSI** (WiX v3 via Tauri) and **NSIS** `-setup.exe`. **MSIX** is an optional Microsoft Store path (see `MSIX.md`); Tauri 2.12.x does not emit MSIX (`tauri build --bundles` accepts `msi` and `nsis` only; verified against `@tauri-apps/cli` 2.12.4 help and [Windows Installer](https://v2.tauri.app/distribute/windows-installer/) docs).

Official sources re-checked for this task:

| Topic | URL |
|---|---|
| Tauri Windows installer | https://v2.tauri.app/distribute/windows-installer/ |
| Tauri Windows code signing | https://v2.tauri.app/distribute/sign/windows/ |
| D5 cost / format decision | `spikes/D5.md` |

## Layout

| Path | Role |
|---|---|
| `uninstall-restore.ps1` | AC-7.3: calls `hertzline-helper restore_all --reason uninstall` before binaries are removed |
| `nsis-hooks.nsh` | NSIS `NSIS_HOOK_PREUNINSTALL` runs the restore hook |
| `wix/uninstall-restore.wxs` | WiX fragment CustomAction for MSI uninstall restore |
| `tauri.windows.bundle.json` | Merge config for `tauri build` (`bundle.active`, MSI+NSIS, hooks) |
| `SIGNING.md` | Authenticode / Artifact Signing; fail closed; never silent `--no-sign` |
| `MSIX.md` | Store-optional MSIX notes and sandbox limits |

## Build (local / CI)

From the `packaging` repo root on Windows:

```text
python scripts/build_windows.py
```

The script:

1. Resolves sibling `../app` and optional `../helper` release binary.
2. Stages `hertzline-helper.exe` into `app/src-tauri/binaries/` when present (external bin naming for Tauri).
3. Runs `npx tauri build --bundles msi,nsis --ci -c <packaging>/windows/tauri.windows.bundle.json` in `app`.
4. Copies produced installers into `packaging/dist/windows/<version>/`.
5. Writes SHA-256 checksums via `scripts/checksums.py`.

Dry-run (docs + script gates only, no Tauri compile):

```text
python scripts/build_windows.py --check-only
```

## Uninstall restore (AC-7.3)

Both installer families must invoke restore **before** deleting files:

```text
hertzline-helper restore_all --reason uninstall --json
```

NSIS: `NSIS_HOOK_PREUNINSTALL` in `nsis-hooks.nsh`.  
MSI: WiX CustomAction `HertzlineRestoreAll` scheduled before `RemoveFiles`.  
Manual / packaging CI: `windows/uninstall-restore.ps1`.

## Signing

Public releases **must** be Authenticode-signed. See `SIGNING.md`. Owner supplies cert (Azure Artifact Signing Basic or OV). Agent never purchases certs or uses `--no-sign` for a public release job.

```text
python scripts/sign_windows.py --public --artifacts dist/windows/<version>
```

Without credentials, `--public` exits non-zero (fail closed).

## Checksums

```text
python scripts/checksums.py dist/windows/<version>
```

Writes `SHA256SUMS.txt` next to the artifacts (filename + hex digest per line).
