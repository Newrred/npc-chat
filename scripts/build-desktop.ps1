param([switch]$Shortcut)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$dotnet = Join-Path $repo '.runtime/dotnet/dotnet.exe'
if (!(Test-Path -LiteralPath $dotnet)) { $dotnet = 'dotnet' }
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$output = Join-Path $repo '.runtime/desktop-app'
Push-Location (Join-Path $repo 'desktop')
try {
    & $dotnet publish 'NpcChat.Desktop/NpcChat.Desktop.csproj' -c Release -r win-x64 --self-contained true -o $output
    if ($LASTEXITCODE -ne 0) { throw 'Desktop publish failed' }
} finally { Pop-Location }
if ($Shortcut) {
    $linkPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'NPC Chat.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($linkPath)
    $exe = Join-Path $output 'NpcChat.Desktop.exe'
    if ((Test-Path -LiteralPath $linkPath) -and $link.TargetPath -ne $exe) {
        throw 'An unrelated NPC Chat shortcut already exists; it was not replaced.'
    }
    $link.TargetPath = $exe
    $link.Arguments = '--root "' + $repo + '"'
    $link.WorkingDirectory = $repo
    $link.Description = 'NPC Chat — 바탕화면 캐릭터 채팅'
    $link.Save()
    Write-Output "Shortcut ready: $linkPath"
}
