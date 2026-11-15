# Hertzline Windows uninstall restore hook (HZ-018 / HZ-049 / AC-7.3).
# Invoked by the MSI/NSIS uninstall sequence before binaries are removed.
# Does not require the desktop UI.

param(
    [string]$HelperPath = "",
    [string]$StorePath = ""
)

$ErrorActionPreference = "Stop"

if (-not $HelperPath) {
    $candidates = @(
        (Join-Path $PSScriptRoot "hertzline-helper.exe"),
        (Join-Path $PSScriptRoot "resources\hertzline-helper.exe"),
        (Join-Path (Split-Path $PSScriptRoot -Parent) "hertzline-helper.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $HelperPath = $candidate
            break
        }
    }
}

if (-not $HelperPath) {
    $cmd = Get-Command hertzline-helper -ErrorAction SilentlyContinue
    if ($cmd) {
        $HelperPath = $cmd.Source
    } else {
        $HelperPath = Join-Path $PSScriptRoot "..\..\helper\target\release\hertzline-helper.exe"
    }
}

if (-not (Test-Path -LiteralPath $HelperPath)) {
    Write-Error "hertzline-helper not found at '$HelperPath'"
    exit 1
}

$argList = @("restore_all", "--reason", "uninstall", "--json")
if ($StorePath) {
    $argList += @("--store", $StorePath)
}

Write-Host "Invoking: $HelperPath $($argList -join ' ')"
& $HelperPath @argList
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Error "restore_all failed with exit code $code"
    exit $code
}
exit 0
