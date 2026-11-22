[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Zig,
    [Parameter(Mandatory)][string]$MakeAppx
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$out = Join-Path $PSScriptRoot 'dist'
$packageFiles = Join-Path $out 'package-files'
New-Item -ItemType Directory -Path $packageFiles -Force | Out-Null
$zigPath = (Resolve-Path -LiteralPath $Zig).Path
$makeAppxPath = (Resolve-Path -LiteralPath $MakeAppx).Path
$compilerArguments = @(
    'c++', '-target', 'x86_64-windows-gnu', '-std=c++17', '-g0', '-O2', '-Wall', '-Wextra'
    '-Wno-dll-attribute-on-redeclaration', '-shared', (Join-Path $PSScriptRoot 'explorer_command.cpp')
    '-lole32', '-lshlwapi', '-luuid', '-ladvapi32', '-o', (Join-Path $out 'ExplorerCommand.dll')
)
& $zigPath @compilerArguments
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
