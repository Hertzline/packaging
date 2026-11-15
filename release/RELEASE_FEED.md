# Release feed -> website (HZ-052)

Static website downloads and changelog read `website/src/data/releases.json`.
Packaging owns the producer: `scripts/write_release_metadata.py`.

## Contract

| Field | Source | Notes |
|---|---|---|
| `status` | `--status` | `not_released` (default honest empty) or `released` |
| `latest.version` | `--version` | SemVer without leading `v` |
| `latest.published` | `--published` | `YYYY-MM-DD` |
| `latest.minOs` | script defaults | Windows 10 / Linux x86_64 baseline / macOS 13.0 |
| `artifacts.<os>[]` | `--*-sums` + `--base-url` | `id`, `label`, `url`, SHA-256 (`sha256`), optional `sizeBytes` |
| `history[]` | version + highlights | Changelog feed; empty while `not_released` |
| `wingetId` | fixed | `Hertzline.Hertzline` |
| Secrets | never | Private keys, tokens, certs rejected |

Artifact URLs are public HTTPS only:

```text
{base-url}/{windows|linux|macos}/{filename}
```

Example base: `https://github.com/Hertzline/app/releases/download/v0.1.0`

## Produce a feed (owner / release CI)

1. Build and sign OS artifacts (HZ-049 / HZ-050 / HZ-051).
2. Ensure each OS output dir has `SHA256SUMS.txt` from `scripts/checksums.py`.
3. Preserve website UI/copy by passing the live template:

```bash
python scripts/write_release_metadata.py \
  --version 0.1.0 \
  --published 2026-11-15 \
  --status released \
  --base-url https://github.com/Hertzline/app/releases/download/v0.1.0 \
  --windows-sums dist/windows/0.1.0/SHA256SUMS.txt \
  --linux-sums dist/linux/0.1.0/SHA256SUMS.txt \
  --macos-sums dist/macos/0.1.0/SHA256SUMS.txt \
  --template ../website/src/data/releases.json \
  --highlight-en "First measured-release candidate" \
  --highlight-it "Primo release candidate misurato" \
  -o ../website/src/data/releases.json
```

4. Commit the updated `releases.json` in `website` (no secrets). Owner deploys Vercel; agents never deploy.
5. Keep `--status not_released` until signed public artifacts exist.

## Checks

```bash
python scripts/check_hz052.py
```

## Non-goals

- No winget-pkgs PR (HZ-054, owner approval).
- No Vercel CLI / deploy.
- No embedding of signing keys or Apple/Authenticode credentials.
