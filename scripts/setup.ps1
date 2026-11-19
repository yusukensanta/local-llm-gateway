#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$SkipVenv)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 3.11+ is required." }
$Version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$Version -lt [version]"3.11") { throw "Python 3.11+ required; found $Version." }
if (-not $SkipVenv) {
    $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if ($PSCmdlet.ShouldProcess($VenvPython, "Create virtual environment")) {
        if (-not (Test-Path $VenvPython)) { & python -m venv (Join-Path $Root ".venv") }
    }
} else { $VenvPython = (Get-Command python).Source }
if ($PSCmdlet.ShouldProcess("dependencies", "Install project")) {
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -e ".[dev]"
}
