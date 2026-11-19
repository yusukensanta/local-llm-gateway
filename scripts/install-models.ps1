#Requires -Version 5.1
<#
.SYNOPSIS
Pull Ollama models. Defaults to the project's default model.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param([string[]]$Models = @($(if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5-coder:7b" })))
$ErrorActionPreference = "Stop"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "Install Ollama first." }
foreach ($Model in $Models) {
    if ($PSCmdlet.ShouldProcess($Model, "Pull Ollama model")) {
        & ollama pull $Model
        if ($LASTEXITCODE -ne 0) { throw "Failed to pull $Model" }
    }
}
