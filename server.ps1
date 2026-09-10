param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$runtimePython = Join-Path $projectRoot "venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $runtimePython)) {
    $runtimePython = Join-Path $projectRoot ".venv/Scripts/python.exe"
}
if (-not (Test-Path -LiteralPath $runtimePython)) {
    $runtimePython = "python"
}

Push-Location $projectRoot
try {
    & $runtimePython (Join-Path $projectRoot "scripts/server_runtime.py") $Action `
        --env-file (Join-Path $projectRoot ".runtime/public-test.env")
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
