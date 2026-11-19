#Requires -Version 5.1
<#
.SYNOPSIS
Register the MCP server with Claude Code (user scope) for one workspace.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param([string]$Workspace = (Get-Location).Path)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run scripts/setup.ps1 first." }
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { throw "Claude Code CLI not found." }
$ResolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
if ($PSCmdlet.ShouldProcess("Claude Code MCP registry", "Register local-llm")) {
    # Replace a previous registration so re-running the script is idempotent.
    try { & claude mcp remove local-llm --scope user 2>&1 | Out-Null } catch { $null = $_ }
    $global:LASTEXITCODE = 0
    & claude mcp add local-llm --scope user --env "LOCAL_LLM_WORKSPACE=$ResolvedWorkspace" -- $Python -m local_llm.server
    if ($LASTEXITCODE -ne 0) { throw "MCP registration failed." }
    Write-Host "Registered local-llm for workspace: $ResolvedWorkspace"
}
