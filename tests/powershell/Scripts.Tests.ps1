BeforeAll {
    $script:ScriptsDir = Join-Path $PSScriptRoot "../../scripts"
    function Get-ScriptText([string]$Name) { Get-Content (Join-Path $script:ScriptsDir $Name) -Raw }
}

Describe "PowerShell scripts" {
    It "<_> parses without syntax errors" -ForEach (Get-ChildItem (Join-Path $PSScriptRoot "../../scripts") -Filter "*.ps1" | ForEach-Object Name) {
        $tokens = $null; $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $script:ScriptsDir $_), [ref]$tokens, [ref]$errors) | Out-Null
        $errors | Should -BeNullOrEmpty
    }

    It "<_> stops on errors" -ForEach (Get-ChildItem (Join-Path $PSScriptRoot "../../scripts") -Filter "*.ps1" | ForEach-Object Name) {
        Get-ScriptText $_ | Should -Match '\$ErrorActionPreference = "Stop"'
    }

    It "<_> supports -WhatIf" -ForEach @("setup.ps1", "install-models.ps1", "register-mcp.ps1") {
        Get-ScriptText $_ | Should -Match "SupportsShouldProcess"
    }

    It "setup uses uv with the lockfile and Python 3.14, not pip" {
        $text = Get-ScriptText "setup.ps1"
        $text | Should -Match "--locked"
        $text | Should -Match '"3\.14"'
        $text | Should -Not -Match "pip install"
    }

    It "MCP registration is user scoped" {
        Get-ScriptText "register-mcp.ps1" | Should -Match "--scope user"
    }
}

Describe "Script behaviour" {
    It "setup fails clearly when uv is missing" {
        $env:PATH_BACKUP = $env:PATH
        try {
            $env:PATH = ""
            { & (Join-Path $script:ScriptsDir "setup.ps1") } | Should -Throw "*uv is required*"
        } finally { $env:PATH = $env:PATH_BACKUP }
    }

    It "install-models fails clearly when ollama is missing" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq "ollama" }
        { & (Join-Path $script:ScriptsDir "install-models.ps1") } | Should -Throw "*Install Ollama first*"
    }

    It "install-models -WhatIf does not pull" {
        Mock Get-Command { [pscustomobject]@{ Name = "ollama" } } -ParameterFilter { $Name -eq "ollama" }
        { & (Join-Path $script:ScriptsDir "install-models.ps1") -Models "x:1" -WhatIf } | Should -Not -Throw
    }
}
