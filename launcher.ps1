#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ProblemList,
    [Parameter(Mandatory)][string]$Submissions,
    [int]$Port = 8765,
    [string]$DataDir,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    $venvPython = Join-Path $PSScriptRoot '.venv/bin/python'
}
$pythonCommand = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { 'python' }
$launchArgs = @((Join-Path $PSScriptRoot 'launcher.py'), '--problem-list', $ProblemList, '--submissions', $Submissions, '--port', "$Port")
if ($DataDir) { $launchArgs += @('--data-dir', $DataDir) }
if ($NoBrowser) { $launchArgs += '--no-browser' }
& $pythonCommand @launchArgs
exit $LASTEXITCODE
