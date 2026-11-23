[CmdletBinding()]
param(
    [string]$Zig,
    [Parameter(Mandatory)][string]$MakeAppx,
    [switch]$Msvc
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$out = Join-Path $PSScriptRoot 'dist'
$packageFiles = Join-Path $out 'package-files'
New-Item -ItemType Directory -Path $packageFiles -Force | Out-Null
$makeAppxPath = (Resolve-Path -LiteralPath $MakeAppx).Path
if ($Msvc) {
    $compiler = (Get-Command cl.exe -ErrorAction Stop).Source
    $compilerArguments = @(
        '/nologo', '/std:c++17', '/EHsc', '/W4', '/O2', '/MT', '/LD',
        ('/Fo:' + (Join-Path $out 'ExplorerCommand.obj')), (Join-Path $PSScriptRoot 'explorer_command.cpp'),
        '/link', ('/def:' + (Join-Path $PSScriptRoot 'ExplorerCommand.def')),
        ('/out:' + (Join-Path $out 'ExplorerCommand.dll')),
        ('/implib:' + (Join-Path $out 'ExplorerCommand.lib')),
        'ole32.lib', 'shlwapi.lib', 'uuid.lib', 'advapi32.lib', 'user32.lib'
    )
} else {
    if (!$Zig) { throw 'Supply -Zig or run with -Msvc.' }
    $compiler = (Resolve-Path -LiteralPath $Zig).Path
    $compilerArguments = @(
        'c++', '-target', 'x86_64-windows-gnu', '-std=c++17', '-g0', '-O2', '-Wall', '-Wextra',
        '-shared', (Join-Path $PSScriptRoot 'explorer_command.cpp'), (Join-Path $PSScriptRoot 'ExplorerCommand.def'),
        '-lole32', '-lshlwapi', '-luuid', '-ladvapi32', '-luser32', '-o', (Join-Path $out 'ExplorerCommand.dll')
    )
}
& $compiler @compilerArguments
if ($LASTEXITCODE -ne 0) { throw 'Explorer extension compilation failed.' }

Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'AppxManifest.xml') -Destination $packageFiles
$makeIcons = @'
from pathlib import Path
from sys import argv
from PIL import Image

with Image.open(argv[1]) as source:
    for name, pixels in (("StoreLogo.png", 50), ("AppLogo.png", 150), ("SmallLogo.png", 44)):
        source.resize((pixels, pixels), Image.Resampling.LANCZOS).save(Path(argv[2]) / name)
'@
$python = Join-Path $project '.venv\Scripts\python.exe'
& $python -c $makeIcons (Join-Path $project 'assets\logo.png') $packageFiles
if ($LASTEXITCODE -ne 0) { throw 'Explorer package icon generation failed.' }

& $makeAppxPath pack /d $packageFiles /p (Join-Path $out 'ExplorerMenu.msix') /o /nv
if ($LASTEXITCODE -ne 0) { throw 'Explorer package creation failed.' }
