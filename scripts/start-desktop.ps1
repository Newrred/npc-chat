param([switch]$Fake)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$published = Join-Path $repo '.runtime/desktop-app/NpcChat.Desktop.exe'
if (Test-Path -LiteralPath $published) {
    $launchArgs = '--root "' + $repo + '"'
    if ($Fake) { $launchArgs += ' --fake' }
    Start-Process -FilePath $published -ArgumentList $launchArgs -WorkingDirectory $repo -WindowStyle Hidden
    return
}
$dotnet = Join-Path $repo '.runtime/dotnet/dotnet.exe'
$app = Join-Path $repo 'desktop/NpcChat.Desktop/bin/Release/net10.0-windows/NpcChat.Desktop.dll'
if (!(Test-Path -LiteralPath $dotnet) -or !(Test-Path -LiteralPath $app)) {
    throw 'Desktop build missing. Follow docs/DESKTOP_APP.md first.'
}
$launchArgs = '"' + $app + '" --root "' + $repo + '"'
if ($Fake) { $launchArgs += ' --fake' }
Start-Process -FilePath $dotnet -ArgumentList $launchArgs -WorkingDirectory $repo -WindowStyle Hidden
