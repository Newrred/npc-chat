# Arguments are forwarded to the shared launcher, e.g. --model "...gguf".
$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$runtimePython = Join-Path $repositoryRoot "venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $runtimePython)) { $runtimePython = Join-Path $repositoryRoot ".venv/Scripts/python.exe" }
if (-not (Test-Path -LiteralPath $runtimePython)) { $runtimePython = "python" }
& $runtimePython (Join-Path $PSScriptRoot "benchmark_local.py") @args
exit $LASTEXITCODE
