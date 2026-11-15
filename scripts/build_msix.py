#!/usr/bin/env python3
"""MSIX stub for Hertzline (HZ-049).

Tauri 2.12.x does not produce MSIX. Store packaging stays owner-gated.
See windows/MSIX.md.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "unavailable: MSIX is not built for v1 direct download. "
        "Public Windows artifacts are MSI + NSIS (Tauri --bundles msi,nsis). "
        "Microsoft Store MSIX requires owner approval and Partner Center packaging. "
        "See windows/MSIX.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
