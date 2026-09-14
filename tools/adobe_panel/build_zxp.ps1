<#
  build_zxp.ps1 - Empaqueta y firma el panel CEP como .zxp instalable.

  Requiere ZXPSignCmd.exe de Adobe (no viene con Windows). Descarga:
    https://github.com/Adobe-CEP/CEP-Resources  ->  carpeta "ZXPSignCMD"

  Uso tipico:
    powershell -ExecutionPolicy Bypass -File build_zxp.ps1 -ZXPSignCmd "C:\ruta\ZXPSignCmd.exe"

  Si ZXPSignCmd esta en el PATH, basta:
    powershell -ExecutionPolicy Bypass -File build_zxp.ps1

  Genera (si no existe) un certificado autofirmado y produce:
    ..\adobe_panel_dist\com.vibo.adobepanel.zxp
#>
param(
  [string]$ZXPSignCmd = "",
  [string]$Source       = "$PSScriptRoot",
  [string]$Output       = "$PSScriptRoot\..\adobe_panel_dist\com.vibo.adobepanel.zxp",
  [string]$Cert         = "$PSScriptRoot\..\adobe_panel_dist\vibo_cert.p12",
  [string]$CertPassword = "vibo1234",
  [string]$TSA          = "http://timestamp.digicert.com"
)

# Localizar ZXPSignCmd
if (-not $ZXPSignCmd) {
  $cmd = Get-Command ZXPSignCmd -ErrorAction SilentlyContinue
  if ($cmd) { $ZXPSignCmd = $cmd.Source }
}
if (-not $ZXPSignCmd -or -not (Test-Path $ZXPSignCmd)) {
  Write-Error "No encuentro ZXPSignCmd.exe. Pasa -ZXPSignCmd 'C:\ruta\ZXPSignCmd.exe'. Descarga en Adobe-CEP/CEP-Resources."
  exit 1
}

$distDir = Split-Path $Output -Parent
New-Item -ItemType Directory -Force -Path $distDir | Out-Null

# Certificado autofirmado (solo la primera vez)
if (-not (Test-Path $Cert)) {
  Write-Host "Generando certificado autofirmado..."
  & $ZXPSignCmd -selfSignedCert US CA "Vibo" "Vibo Adobe Panel" $CertPassword $Cert
  if ($LASTEXITCODE -ne 0) { Write-Error "Fallo al crear el certificado."; exit 1 }
}

if (Test-Path $Output) { Remove-Item $Output -Force }

Write-Host "Firmando panel desde: $Source"
& $ZXPSignCmd -sign $Source $Output $Cert $CertPassword -tsa $TSA
if ($LASTEXITCODE -ne 0) { Write-Error "Fallo la firma."; exit 1 }

Write-Host ""
Write-Host "Listo: $Output"
Write-Host "Instalacion: usa un ZXP Installer (Anastasiy) o ExManCmd (ver README.md)."
