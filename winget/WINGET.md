# winget manifests for `Hertzline.Hertzline` (HZ-053)

Draft multi-file manifests for the Windows Package Manager community repository. **Do not open a PR to `microsoft/winget-pkgs` without explicit owner approval** (HZ-054 / `RULES.md`).

## Package ID and install string

| Item | Value |
|---|---|
| PackageIdentifier | `Hertzline.Hertzline` |
| Install command (docs + website) | `winget install Hertzline.Hertzline` |
| Publisher partition path | `manifests/h/Hertzline/Hertzline/<version>/` |

Official docs used for this draft (re-verified 2026-11-15):

| Topic | URL |
|---|---|
| Create a package manifest | https://learn.microsoft.com/en-us/windows/package-manager/package/manifest |
| Schema 1.12.0 | https://github.com/microsoft/winget-pkgs/tree/master/doc/manifest/schema/1.12.0 |
| Installer schema | https://github.com/microsoft/winget-pkgs/blob/master/doc/manifest/schema/1.12.0/installer.md |
| Default locale schema | https://github.com/microsoft/winget-pkgs/blob/master/doc/manifest/schema/1.12.0/defaultLocale.md |
| Validation | https://github.com/microsoft/winget-pkgs/blob/master/doc/Validation.md |
| `winget validate` | `winget validate --manifest <dir>` |

As of 2026-11-15, `manifests/h/Hertzline` is still absent upstream (HTTP 404).

## Layout

```text
winget/manifests/h/Hertzline/Hertzline/<PackageVersion>/
  Hertzline.Hertzline.yaml                 # ManifestType: version
  Hertzline.Hertzline.locale.en-US.yaml    # ManifestType: defaultLocale
  Hertzline.Hertzline.installer.yaml       # ManifestType: installer (WiX MSI)
```

`ManifestVersion` is **1.12.0** (current winget-pkgs schema folder as of 2026-11-15; Learn docs sample and wingetcreate 1.12.x).

## Installer choice

D5 chose **MSI (WiX) + NSIS** for Windows. This draft publishes the **WiX MSI** only (`InstallerType: wix`) because silent install and ProductCode correlation are first-class for MSI. NSIS remains a direct-download artifact; it is not required in the winget manifest for v1.

Installer URL pattern (filled at release):

```text
https://github.com/Hertzline/app/releases/download/v<version>/Hertzline_<version>_x64_en-US.msi
```

SHA-256 and `ProductCode` must match the signed release MSI. The `0.0.0` draft values were taken from the local HZ-049 build under `dist/windows/0.0.0/` (unsigned local probe; not a public release).

ARP `Publisher` from that MSI is `hertzline` (Tauri Manufacturer); `AppsAndFeaturesEntries.Publisher` matches that string for list/upgrade correlation. Locale `Publisher` stays `Hertzline` to match the PackageIdentifier publisher folder.

## Pre-release honesty

- Package version `0.0.0` is a packaging draft, not a public GitHub Release.
- The InstallerUrl for `v0.0.0` is **not live** until a signed release exists.
- Website `/download/` keeps `wingetPublished: false` until HZ-054 lands with owner approval.
- `winget validate` checks schema locally; it does not prove the URL downloads.

## Refresh before a real submission

1. Build and Authenticode-sign the MSI (`scripts/build_windows.py`, `scripts/sign_windows.py --public`).
2. Publish the asset to `Hertzline/app` GitHub Releases at tag `vX.Y.Z`.
3. Copy manifests to `winget/manifests/h/Hertzline/Hertzline/X.Y.Z/`.
4. Set `PackageVersion`, `InstallerUrl`, `InstallerSha256`, and `ProductCode` from the signed MSI.
5. Run `python scripts/check_hz053.py` and `winget validate --manifest <version-dir>`.
6. Stop. Owner opens the winget-pkgs PR only after explicit approval (HZ-054).

## Local checks

```bash
python scripts/check_hz053.py
winget validate --manifest winget/manifests/h/Hertzline/Hertzline/0.0.0
```
