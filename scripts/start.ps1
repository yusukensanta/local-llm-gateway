#Requires -Version 5.1
<#
.SYNOPSIS
Start the MCP server on stdio (normally launched by Claude Code, not by hand).
#>
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run scripts/setup.ps1 first." }
& $Python -m local_llm.server
exit $LASTEXITCODE
