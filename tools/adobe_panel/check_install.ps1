<#
  check_install.ps1 - Diagnoses the local CEP install for Vibo Adobe Panel.

  Read-only by default. It checks:
  - PlayerDebugMode registry keys for common CSXS versions.
  - Whether the CEP extension folder exists.
  - Whether the extension is a symlink/junction/copy.
  - Whether config.json points to the repo tools directory.

  Usage:
    powershell -ExecutionPolicy Bypass -File tools\adobe_panel\check_install.ps1
#>
param(
  [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path,
  [string]$ExtensionId = "com.vibo.adobepanel"
)

$ErrorActionPreference = "Stop"

function StatusLine([string]$State, [string]$Message) {
  "{0,-7} {1}" -f $State, $Message
}

$repoTools = Join-Path $RepoRoot "tools"
$panelSource = Join-Path $repoTools "adobe_panel"
$extensionRoot = Join-Path $env:APPDATA "Adobe\CEP\extensions\$ExtensionId"
$prefsDir = Join-Path $env:APPDATA "Adobe\CEP\preferences\vibo_adobe_panel"
$prefsConfig = Join-Path $prefsDir "config.json"
$probeScript = Join-Path $repoTools "illustrator\scripts\logo_clean_master.jsx"

Write-Host "# Vibo Adobe Panel install check"
Write-Host ""
Write-Host ("RepoRoot:      {0}" -f $RepoRoot)
Write-Host ("Repo tools:    {0}" -f $repoTools)
Write-Host ("Extension dir: {0}" -f $extensionRoot)
Write-Host ""

foreach ($version in 9..13) {
  $key = "HKCU:\Software\Adobe\CSXS.$version"
  $value = $null
  if (Test-Path $key) {
    $value = (Get-ItemProperty -Path $key -Name PlayerDebugMode -ErrorAction SilentlyContinue).PlayerDebugMode
  }
  if ($value -eq "1") {
    StatusLine "OK" "CSXS.$version PlayerDebugMode=1"
  } else {
    StatusLine "WARN" "CSXS.$version PlayerDebugMode is not 1"
  }
}

if (Test-Path $probeScript) {
  StatusLine "OK" "Illustrator scripts found in repo tools"
} else {
  StatusLine "FAIL" "Missing $probeScript"
}

if (Test-Path $extensionRoot) {
  $item = Get-Item $extensionRoot -Force
  $linkType = if ($item.LinkType) { $item.LinkType } else { "copy/directory" }
  StatusLine "OK" "CEP extension exists ($linkType)"
} else {
  StatusLine "FAIL" "CEP extension is not installed"
  StatusLine "HINT" "Prefer symlink: New-Item -ItemType SymbolicLink -Path `"$extensionRoot`" -Target `"$panelSource`""
}

if (Test-Path (Join-Path $extensionRoot "CSXS\manifest.xml")) {
  StatusLine "OK" "manifest.xml present"
} else {
  StatusLine "FAIL" "manifest.xml missing from extension"
}

if (Test-Path $prefsConfig) {
  try {
    $cfg = Get-Content $prefsConfig -Raw | ConvertFrom-Json
    if ($cfg.repo_tools_path -and (Test-Path (Join-Path $cfg.repo_tools_path "illustrator\scripts\logo_clean_master.jsx"))) {
      StatusLine "OK" "preferences repo_tools_path resolves"
    } else {
      StatusLine "WARN" "preferences config exists but repo_tools_path does not resolve"
    }
  } catch {
    StatusLine "WARN" "preferences config is not valid JSON"
  }
} else {
  StatusLine "INFO" "no preferences config; symlink/repo fallback or env var must resolve tools"
}

Write-Host ""
Write-Host "If Illustrator/Photoshop/After Effects is already open, restart it after changing CEP files or registry keys."
