# Hertzline Windows uninstall restore hook (HZ-018 / AC-7.3).
# Invoked by the MSI/NSIS uninstall sequence before binaries are removed.
# Does not require the desktop UI.

param(
    [string]$HelperPath = "",
    [string]$StorePath = ""
)

$ErrorActionPreference = "Stop"

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

$args = @("restore_all", "--reason", "uninstall", "--json")
if ($StorePath) {
    $args += @("--store", $StorePath)
}

Write-Host "Invoking: $HelperPath $($args -join ' ')"
& $HelperPath @args
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Error "restore_all failed with exit code $code"
    exit $code
}
exit 0
