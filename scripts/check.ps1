#Requires -Version 5.1
<#
.SYNOPSIS
Run every quality gate: format check, lint, type check (ty), tests with coverage.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv is required." }
$Steps = @(
    @("ruff", "format", "--check", "."),
    @("ruff", "check", "."),
    @("ty", "check"),
    @("pytest", "--cov")
)
foreach ($Step in $Steps) {
    & uv run --locked @Step
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $($Step -join ' ')" }
}
