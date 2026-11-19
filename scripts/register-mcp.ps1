#Requires -Version 5.1
<#
.SYNOPSIS
Register the MCP server with Claude Code (user scope) for one workspace.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Workspace = (Get-Location).Path,
    [string]$Model,
    # Register even when the local-llm plugin is installed (which duplicates the server).
    [switch]$Force
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run scripts/setup.ps1 first." }
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { throw "Claude Code CLI not found." }
$PluginId = "local-llm@local-llm-gateway"
if (-not $Force) {
    # The plugin already provides this MCP server; a second registration would show up twice.
    $Plugins = ""
    try { $Plugins = (& claude plugin list 2>$null) -join "`n" } catch { $Plugins = "" }
    $global:LASTEXITCODE = 0
    if ($Plugins.Contains($PluginId)) {
        throw "The plugin $PluginId is installed and already provides this MCP server. Re-run with -Force to register anyway, or remove the plugin first: claude plugin uninstall $PluginId"
    }
}
$ResolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
if ($PSCmdlet.ShouldProcess("Claude Code MCP registry", "Register local-llm")) {
    # Replace a previous registration so re-running the script is idempotent.
    try { & claude mcp remove local-llm --scope user 2>&1 | Out-Null } catch { $null = $_ }
    $global:LASTEXITCODE = 0
    $EnvArgs = @("--env", "LOCAL_LLM_WORKSPACE=$ResolvedWorkspace")
    if ($Model) { $EnvArgs += @("--env", "OLLAMA_MODEL=$Model") }
    & claude mcp add local-llm --scope user @EnvArgs -- $Python -m local_llm.server
    if ($LASTEXITCODE -ne 0) { throw "MCP registration failed." }
    Write-Host "Registered local-llm for workspace: $ResolvedWorkspace"
}
