# Deterministic native assets from the authored SVG; no image-service dependency.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore, WindowsBase
$repo = Split-Path -Parent $PSScriptRoot
[xml]$svg = Get-Content -LiteralPath (Join-Path $repo 'frontend/brand.svg') -Raw
$output = Join-Path $repo 'desktop/NpcChat.Desktop/Assets'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$frames = @()
foreach ($size in @(16,24,32,48,64,128,256)) {
    $visual = New-Object Windows.Media.DrawingVisual
    $drawing = $visual.RenderOpen()
    $drawing.PushTransform((New-Object Windows.Media.ScaleTransform ($size/256.0),($size/256.0)))
    $brushes = New-Object Windows.Media.BrushConverter
    $drawing.DrawRoundedRectangle($brushes.ConvertFromString('#7434FF'), $null, (New-Object Windows.Rect 0,0,256,256),58,58)
    foreach ($path in $svg.svg.path) {
        $drawing.DrawGeometry($brushes.ConvertFromString($path.fill),$null,[Windows.Media.Geometry]::Parse($path.d))
    }
    $drawing.Pop(); $drawing.Close()
    $bitmap = New-Object Windows.Media.Imaging.RenderTargetBitmap $size,$size,96,96,([Windows.Media.PixelFormats]::Pbgra32)
    $bitmap.Render($visual)
    $encoder = New-Object Windows.Media.Imaging.PngBitmapEncoder
    $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
    $stream = New-Object IO.MemoryStream
    $encoder.Save($stream)
    $frames += ,@($size,$stream.ToArray())
    if ($size -eq 256) { [IO.File]::WriteAllBytes((Join-Path $output 'brand.png'),$stream.ToArray()) }
    $stream.Dispose()
}
$file = [IO.File]::Create((Join-Path $output 'brand.ico'))
$writer = New-Object IO.BinaryWriter $file
try {
    $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$frames.Count)
    $offset = 6 + 16 * $frames.Count
    foreach ($frame in $frames) {
        $dimension = if ($frame[0] -eq 256) { 0 } else { $frame[0] }
        $writer.Write([byte]$dimension); $writer.Write([byte]$dimension)
        $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]32)
        $writer.Write([uint32]$frame[1].Length); $writer.Write([uint32]$offset)
        $offset += $frame[1].Length
    }
    foreach ($frame in $frames) { $writer.Write([byte[]]$frame[1]) }
} finally { $writer.Dispose(); $file.Dispose() }
Write-Output 'Brand assets built from frontend/brand.svg (7 icon sizes).'
