# Arguments are forwarded to the shared launcher, e.g. --model "...gguf".
$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$runtimePython = Join-Path $repositoryRoot "venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $runtimePython)) { $runtimePython = Join-Path $repositoryRoot ".venv/Scripts/python.exe" }
if (-not (Test-Path -LiteralPath $runtimePython)) { $runtimePython = "python" }
& $runtimePython (Join-Path $PSScriptRoot "local_runtime.py") stop-llm @args
exit $LASTEXITCODE
