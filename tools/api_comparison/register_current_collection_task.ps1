param(
    [Parameter(Mandatory = $true)]
    [string]$PythonPath,

    [string]$ProjectRoot,

    [string]$TaskName = "DryNow Current Weather Collection",

    [ValidateRange(0, 29)]
    [int]$Minute = 5,

    [switch]$WakeToRun,

    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Join-Path $PSScriptRoot "..\.."
}

$resolvedPython = (Resolve-Path -LiteralPath $PythonPath).Path
$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$toolDirectory = Join-Path $resolvedProjectRoot "tools\api_comparison"
$runnerPath = Join-Path $toolDirectory "run_current_collection.ps1"

if (-not (Test-Path -LiteralPath $resolvedPython -PathType Leaf)) {
    throw "Python executable not found: $resolvedPython"
}
if (-not (Test-Path -LiteralPath $runnerPath -PathType Leaf)) {
    throw "Runner script not found: $runnerPath"
}

$projectEnv = Join-Path $resolvedProjectRoot ".env"
$toolEnv = Join-Path $toolDirectory ".env"
if (-not (Test-Path -LiteralPath $projectEnv) -and -not (Test-Path -LiteralPath $toolEnv)) {
    Write-Warning ".env was not found in the project root or tools/api_comparison."
}

$powerShellPath = (Get-Command powershell.exe -ErrorAction Stop).Source
$actionArguments = (
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" ' +
    '-PythonPath "{1}" -ProjectRoot "{2}"'
) -f $runnerPath, $resolvedPython, $resolvedProjectRoot
$actionParameters = @{
    Execute = $powerShellPath
    Argument = $actionArguments
    WorkingDirectory = $toolDirectory
}
$action = New-ScheduledTaskAction @actionParameters

$now = Get-Date
$firstRun = $now.Date.AddHours($now.Hour).AddMinutes($Minute)
while ($firstRun -le $now) {
    $firstRun = $firstRun.AddMinutes(30)
}
$triggerParameters = @{
    Once = $true
    At = $firstRun
    RepetitionInterval = (New-TimeSpan -Minutes 30)
}
$trigger = New-ScheduledTaskTrigger @triggerParameters

$settingsParameters = @{
    StartWhenAvailable = $true
    MultipleInstances = "IgnoreNew"
    RunOnlyIfNetworkAvailable = $true
    ExecutionTimeLimit = (New-TimeSpan -Minutes 30)
}
if ($WakeToRun.IsPresent) {
    $settingsParameters["WakeToRun"] = $true
}
$settings = New-ScheduledTaskSettingsSet @settingsParameters
$wakeToRunStatus = if ($WakeToRun.IsPresent) { "ON" } else { "OFF" }

# InteractiveはAPI通信を許可しつつ、Windowsへパスワードを渡さず登録できる。
$currentIdentity = $null
$currentUserName = ""
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
if ($null -eq $currentIdentity) {
    throw "Current Windows identity could not be determined."
}
$currentUserName = $currentIdentity.Name
if ([string]::IsNullOrWhiteSpace($currentUserName)) {
    throw "Current Windows user could not be determined."
}
$principalParameters = @{
    UserId = $currentUserName
    LogonType = "Interactive"
    RunLevel = "Limited"
}
$principal = New-ScheduledTaskPrincipal @principalParameters

$taskParameters = @{
    Action = $action
    Trigger = $trigger
    Settings = $settings
    Principal = $principal
    Description = "Collect DryNow current weather data every 30 minutes."
}
$task = New-ScheduledTask @taskParameters

if ($ValidateOnly) {
    Write-Output "Task definition validation succeeded."
    Write-Output "Task name: $TaskName"
    Write-Output "First run: $firstRun"
    Write-Output "Interval: 30 minutes"
    Write-Output "WakeToRun: $wakeToRunStatus"
    Write-Output "User: $($principalParameters['UserId'])"
    Write-Output "Python: $resolvedPython"
    Write-Output "Project root: $resolvedProjectRoot"
    return
}

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
Write-Output "Registered task: $TaskName"
Write-Output "First run: $firstRun"
Write-Output "Interval: 30 minutes"
Write-Output "WakeToRun: $wakeToRunStatus"
Write-Output "Python: $resolvedPython"
Write-Output "Project root: $resolvedProjectRoot"
