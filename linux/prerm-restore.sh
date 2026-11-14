#!/usr/bin/env bash
# Hertzline Linux prerm restore hook (HZ-018 / AC-7.3).
# Invoked before package removal. Does not require the desktop UI.
set -euo pipefail

HELPER="${HERTZLINE_HELPER:-hertzline-helper}"
STORE_ARGS=()
if [[ -n "${HERTZLINE_SNAPSHOT_STORE:-}" ]]; then
  STORE_ARGS=(--store "${HERTZLINE_SNAPSHOT_STORE}")
fi

if ! command -v "${HELPER}" >/dev/null 2>&1 && [[ ! -x "${HELPER}" ]]; then
  echo "hertzline-helper not found (${HELPER})" >&2
  exit 1
fi

echo "Invoking: ${HELPER} restore_all --reason uninstall --json ${STORE_ARGS[*]:-}"
"${HELPER}" restore_all --reason uninstall --json "${STORE_ARGS[@]}"
