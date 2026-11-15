# Windows Authenticode signing (HZ-049)

Public Windows MSI and NSIS artifacts must be signed. **Never skip signing silently.** Release scripts fail closed when credentials are missing.

Official guide: [Windows Code Signing | Tauri](https://v2.tauri.app/distribute/sign/windows/) (re-fetched 2026-11-15). Costs and eligibility: `spikes/D5.md` (Azure Artifact Signing Basic **$9.99/mo** when eligible, else OV **$150--300/yr**). Purchases are owner-gated (`RULES.md`).

## Chosen paths (v1)

| Path | When | How Tauri is told |
|---|---|---|
| Azure Artifact Signing | Preferred when eligible (orgs US/CA/EU/UK; individuals US/CA) | `bundle.windows.signCommand` = `artifact-signing-cli ... %1` |
| Traditional OV `.pfx` | Artifact Signing unavailable | `certificateThumbprint` + `digestAlgorithm` + `timestampUrl`, or custom `signCommand` |
| Azure Key Vault + relic | HSM-backed OV | `signCommand` = `relic sign --file %1 ...` |

Do **not** pass `tauri build --no-sign` for public release jobs.

## Environment (public release)

At least one of these must be present or `scripts/sign_windows.py --public` fails:

| Mode | Required |
|---|---|
| Artifact Signing | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, plus `HERTZLINE_ARTIFACT_SIGNING_ENDPOINT`, `HERTZLINE_ARTIFACT_SIGNING_ACCOUNT`, `HERTZLINE_ARTIFACT_SIGNING_PROFILE` |
| OV thumbprint (machine store) | `HERTZLINE_WINDOWS_CERT_THUMBPRINT` (and cert imported); optional `HERTZLINE_WINDOWS_TIMESTAMP_URL` (default DigiCert) |
| Custom | `HERTZLINE_WINDOWS_SIGN_COMMAND` containing `%1` for the file path |

Never commit private keys, `.pfx` files, client secrets, or thumbprints of production certs.

## Local unsigned builds

Allowed for developer iteration only:

```text
python scripts/build_windows.py
# omit --public-sign
```

Artifacts under `dist/windows/` from an unsigned build must not be published to GitHub Releases or `/download/`.

## Verify after signing

```text
signtool verify /pa /v path\to\installer.msi
signtool verify /pa /v path\to\Hertzline_x.y.z_x64-setup.exe
```

Record the tool version and machine OS in `PROGRESS.md` when a real signed build exists. Until the owner supplies a cert, signing checks are **unavailable** (owner-gated), not silently skipped.
