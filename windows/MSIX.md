# MSIX (optional Store path)

D5 chose **MSI + NSIS** for public direct download and winget. MSIX is deferred as an optional Microsoft Store channel.

## Why not Tauri-native

`@tauri-apps/cli` **2.12.4** `tauri build --bundles` possible values: `msi`, `nsis` only (CLI help verified 2026-11-15). There is no Tauri MSIX target in this pin. Store packaging would use Microsoft tooling ([Package a desktop app from source](https://learn.microsoft.com/en-us/windows/msix/package/packaging-uwp-apps) / Partner Center) after owner approval.

## Sandbox / helper limits (from D5)

| Channel | Helper / elevation | Limit |
|---|---|---|
| MSI / NSIS | Host-installed `hertzline-helper` via short-lived `runas` | Full allow-list after install |
| MSIX / Store | Possible AppContainer / capability limits | Some elevate ops may be **not possible**; must be labeled honestly if a Store build ships |

## Script stub

```text
python scripts/build_msix.py
```

Exits with a clear message that MSIX is not built for v1 direct download. No fake Store package is produced.

## Owner gates

- Microsoft Store developer account create/submit: owner only.
- No store submission without explicit approval (`RULES.md`).
