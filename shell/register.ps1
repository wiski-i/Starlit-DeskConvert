[CmdletBinding()]
param(
    [string]$SignTool,
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$identity = 'DosyaDonusturucu.Explorer'
$publisher = 'CN=Dosya Donusturucu Development'
$state = 'HKCU:\Software\DosyaDonusturucu'
$project = Split-Path -Parent $PSScriptRoot
$package = Join-Path $PSScriptRoot 'dist\ExplorerMenu.msix'

if ($Remove) {
    Get-AppxPackage -Name $identity | Remove-AppxPackage
    if (Test-Path -LiteralPath $state) {
        Remove-ItemProperty -LiteralPath $state -Name 'ExplorerPackageFamily' -ErrorAction SilentlyContinue
    }
    return
}

if (!(Test-Path -LiteralPath $package)) {
    throw 'Build the Explorer package first.'
}

if ($SignTool) {
    $signer = (Resolve-Path -LiteralPath $SignTool).Path
    $certificateOptions = @{
        Type = 'CodeSigningCert'
        Subject = $publisher
        CertStoreLocation = 'Cert:\CurrentUser\My'
        KeyExportPolicy = 'NonExportable'
    }
    $certificate = New-SelfSignedCertificate @certificateOptions
    try {
        & $signer sign /fd SHA256 /sha1 $certificate.Thumbprint /s My $package
        if ($LASTEXITCODE -ne 0) { throw 'Explorer package signing failed.' }
        $publicCert = Join-Path $PSScriptRoot 'dist\ExplorerMenu.cer'
        Export-Certificate -Cert $certificate -FilePath $publicCert | Out-Null
        Write-Output $publicCert
    }
    finally {
        Remove-Item -LiteralPath ('Cert:\CurrentUser\My\' + $certificate.Thumbprint) -DeleteKey
    }
    return
}

Add-AppxPackage -Path $package -ExternalLocation $project
$installed = Get-AppxPackage -Name $identity
if (!$installed) { throw 'Windows did not register the Explorer package.' }
New-Item -Path $state -Force | Out-Null
New-ItemProperty -LiteralPath $state -Name 'ExplorerPackageFamily' -PropertyType String -Value $installed.PackageFamilyName -Force | Out-Null
$python = Join-Path $project '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $python) {
    Push-Location -LiteralPath $project
    try {
        & $python -c 'import windows_shell; windows_shell.refresh_presets()'
        if ($LASTEXITCODE -ne 0) { throw 'Could not refresh the Explorer presets.' }
    }
    finally { Pop-Location }
}
Write-Output $installed.PackageFamilyName
