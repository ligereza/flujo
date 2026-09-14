# Launcher for flujo app in desktop mode (native window, no separate browser)
# Run from root: .\launch-flujo.ps1
# Server runs in background thread inside the app process.
# For no console window at all, use the packaged .exe (flujo package) with --noconsole.
Write-Host "Launching flujo desktop app..."
Set-Location $PSScriptRoot
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
	Write-Error "Python launcher (py) was not found in PATH."
	exit 127
}
& $py.Source -m flujo app --desktop
exit $LASTEXITCODE
