# Close only the tunnel recorded by this project's owned-process launcher.
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $stopCode = @'
from scripts.local_runtime import Runtime
runtime = Runtime()
with runtime.locked():
    runtime.stop('tunnel')
'@
    & "$projectRoot/venv/Scripts/python.exe" -c $stopCode
    if ($LASTEXITCODE -ne 0) { throw "Could not stop the owned test tunnel." }
    Write-Output "Public access stopped. Web app and model remain running."
} finally {
    Pop-Location
}
