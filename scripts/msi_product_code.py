#!/usr/bin/env python3
"""Read ProductCode (and UpgradeCode) from a WiX/MSI via WindowsInstaller COM."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def read_msi_property(msi: Path, property_name: str) -> str:
    """Read a Property table value. Windows-only (WindowsInstaller COM)."""
    msi_path = str(msi.resolve())
    # PowerShell + late-bound COM avoids pywin32 StringData quirks.
    ps = f"""
$ErrorActionPreference = 'Stop'
$msi = @'
{msi_path}
'@
$prop = @'
{property_name}
'@
$installer = New-Object -ComObject WindowsInstaller.Installer
$database = $installer.GetType().InvokeMember(
  'OpenDatabase', 'InvokeMethod', $null, $installer, @($msi.Trim(), 0))
$sql = \"SELECT `Value` FROM `Property` WHERE `Property`='$($prop.Trim())'\"
$view = $database.GetType().InvokeMember(
  'OpenView', 'InvokeMethod', $null, $database, @($sql))
$view.GetType().InvokeMember('Execute', 'InvokeMethod', $null, $view, @(,$null))
$record = $view.GetType().InvokeMember('Fetch', 'InvokeMethod', $null, $view, $null)
if ($null -eq $record) {{ throw \"$($prop.Trim()) not found\" }}
$value = $record.GetType().InvokeMember(
  'StringData', 'GetProperty', $null, $record, 1)
if ([string]::IsNullOrWhiteSpace($value)) {{ throw \"empty $($prop.Trim())\" }}
Write-Output $value
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "powershell MSI read failed").strip()
        raise RuntimeError(err)
    value = (result.stdout or "").strip()
    if not value:
        raise RuntimeError(f"empty {property_name} from {msi}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("msi", type=Path)
    parser.add_argument(
        "--property",
        default="ProductCode",
        help="MSI Property table name (default ProductCode)",
    )
    args = parser.parse_args()
    msi = args.msi.resolve()
    if not msi.is_file():
        print(f"FAIL missing {msi}")
        return 1
    try:
        print(read_msi_property(msi, args.property))
    except RuntimeError as exc:
        print(f"FAIL {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
