param(
    [Parameter(Mandatory = $false)] [string] $SourceDir = (Get-Location),
    [Parameter(Mandatory = $false)] [string] $OutputDir = (Join-Path (Get-Location) "output"),
    [Parameter(Mandatory = $false)] [string] $ProductName = "AI Doc To EPUB",
    [Parameter(Mandatory = $false)] [string] $Version = "0.1.0"
)

$ErrorActionPreference = "Stop"

Write-Host "Building MSI for $ProductName ($Version)" -ForegroundColor Cyan

$SourceDir = (Resolve-Path $SourceDir).ProviderPath
$ResolvedOutput = Resolve-Path -Path $OutputDir -ErrorAction SilentlyContinue
if ($ResolvedOutput) {
    $OutputDir = $ResolvedOutput.ProviderPath
} else {
    $OutputDir = (New-Item -ItemType Directory -Path $OutputDir -Force).FullName
}

$VenvPath = Join-Path $SourceDir ".venv-msi"
if (Test-Path $VenvPath) {
    Remove-Item $VenvPath -Recurse -Force
}

Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv $VenvPath

$VenvPython = Join-Path $VenvPath "Scripts/python.exe"
$VenvPip = Join-Path $VenvPath "Scripts/pip.exe"

& $VenvPip install --upgrade pip
& $VenvPip install .
& $VenvPip install pyinstaller

$SpecOutput = Join-Path $SourceDir "dist"
if (Test-Path $SpecOutput) {
    Remove-Item $SpecOutput -Recurse -Force
}

Write-Host "Running PyInstaller..." -ForegroundColor Yellow
& $VenvPython -m PyInstaller `
    --name aioepub `
    --onefile `
    --console `
    --add-data "$(Join-Path $SourceDir 'README.md');." `
    $(Join-Path $SourceDir 'src/ai_doc_to_epub/cli.py')

$ExecutablePath = Join-Path $SourceDir "dist/aioepub.exe"
if (-not (Test-Path $ExecutablePath)) {
    throw "PyInstaller did not produce the expected executable."
}

$WxsPath = Join-Path $SourceDir "dist/aioepub.wxs"
$UpgradeCode = [guid]::NewGuid().ToString()
$GuidComponent = [guid]::NewGuid().ToString()

@"
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*"
           Name="$ProductName"
           Language="2052"
           Version="$Version"
           Manufacturer="ATOE"
           UpgradeCode="$UpgradeCode">
    <Package InstallerVersion="510" Compressed="yes" InstallScope="perMachine" />
    <MajorUpgrade AllowDowngrades="no" DowngradeErrorMessage="A newer version is already installed." />
    <MediaTemplate />
    <Feature Id="MainFeature" Title="$ProductName" Level="1" Absent="disallow" ConfigurableDirectory="INSTALLFOLDER">
      <Component Id="cmpMainExe" Guid="$GuidComponent" Win64="no">
        <File Id="filAppExe" Source="$ExecutablePath" KeyPath="yes" />
        <Shortcut Id="DesktopShortcut" Directory="DesktopFolder" Name="$ProductName" WorkingDirectory="INSTALLFOLDER" Advertise="yes" />
        <Shortcut Id="ProgramMenuShortcut" Directory="ProgramMenuFolder" Name="$ProductName" WorkingDirectory="INSTALLFOLDER" Advertise="yes" />
        <RemoveFile Id="ProgramMenuShortcutRemove" On="uninstall" Name="$ProductName.lnk" Directory="ProgramMenuFolder" />
      </Component>
    </Feature>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="$ProductName">
          <ComponentRef Id="cmpMainExe" />
        </Directory>
      </Directory>
      <Directory Id="ProgramMenuFolder" Name="Programs" />
      <Directory Id="DesktopFolder" Name="Desktop" />
    </Directory>
  </Product>
</Wix>
"@ | Set-Content -Path $WxsPath -Encoding UTF8

Write-Host "Compiling WiX manifest..." -ForegroundColor Yellow
candle.exe -o (Join-Path $SourceDir "dist/") $WxsPath
$WixObj = Join-Path $SourceDir "dist/aioepub.wixobj"
light.exe -ext WixUIExtension -o (Join-Path $OutputDir "aioepub-$Version.msi") $WixObj

Write-Host "MSI package created at $(Join-Path $OutputDir "aioepub-$Version.msi")" -ForegroundColor Green
