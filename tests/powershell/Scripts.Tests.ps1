Describe "PowerShell scripts" {
    It "parses all PowerShell scripts without syntax errors" {
        $root = Join-Path $PSScriptRoot "../../scripts"
        Get-ChildItem $root -Filter "*.ps1" -Recurse | ForEach-Object {
            $tokens = $null; $errors = $null
            [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors) | Out-Null
            $errors | Should -BeNullOrEmpty
        }
    }
    It "setup and install scripts support WhatIf" {
        (Get-Content (Join-Path $PSScriptRoot "../../scripts/setup.ps1") -Raw) | Should -Match "SupportsShouldProcess"
        (Get-Content (Join-Path $PSScriptRoot "../../scripts/install-models.ps1") -Raw) | Should -Match "SupportsShouldProcess"
    }
    It "MCP registration is scoped to user" {
        (Get-Content (Join-Path $PSScriptRoot "../../scripts/register-mcp.ps1") -Raw) | Should -Match "--scope user"
    }
}
