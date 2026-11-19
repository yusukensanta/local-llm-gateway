#Requires -Version 5.1
<#
.SYNOPSIS
Create .venv with Python 3.14 and install locked dependencies using uv.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$NoDev)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it: https://docs.astral.sh/uv/getting-started/installation/"
}
$UvArgs = @("sync", "--locked", "--python", "3.14")
if ($NoDev) { $UvArgs += "--no-dev" }
if ($PSCmdlet.ShouldProcess($Root, "uv $($UvArgs -join ' ')")) {
    & uv @UvArgs
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed." }
    Write-Host "Setup complete. Run tests with: .\scripts\check.ps1"
}
