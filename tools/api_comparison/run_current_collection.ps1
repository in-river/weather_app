param(
    [Parameter(Mandatory = $true)]
    [string]$PythonPath,

    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Join-Path $PSScriptRoot "..\.."
}

$resolvedPython = (Resolve-Path -LiteralPath $PythonPath).Path
$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$toolDirectory = Join-Path $resolvedProjectRoot "tools\api_comparison"
$collectorPath = Join-Path $toolDirectory "collect_current.py"
$logDirectory = Join-Path $toolDirectory "logs"

if (-not (Test-Path -LiteralPath $resolvedPython -PathType Leaf)) {
    throw "Python executable not found: $resolvedPython"
}
if (-not (Test-Path -LiteralPath $collectorPath -PathType Leaf)) {
    throw "Collector not found: $collectorPath"
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$runId = Get-Date -Format "yyyyMMdd_HHmmss_fff"
$stdoutPath = Join-Path $logDirectory "collect_current_${runId}_stdout.log"
$stderrPath = Join-Path $logDirectory "collect_current_${runId}_stderr.log"

Push-Location $toolDirectory
try {
    & $resolvedPython $collectorPath 1>> $stdoutPath 2>> $stderrPath
    $exitCode = $LASTEXITCODE
}
catch {
    $_ | Out-File -LiteralPath $stderrPath -Append -Encoding utf8
    $exitCode = 1
}
finally {
    Pop-Location
}

exit $exitCode
