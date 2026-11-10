[CmdletBinding()]
param(
  [string]$RoboCasaRoot,
  [string]$Task = "CloseFridge",
  [ValidateSet("target", "pretrain", "all")]
  [string]$Split = "target",
  [string]$KitchenScene = "",
  [ValidateRange(0, [int]::MaxValue)]
  [int]$Seed = 42,
  [ValidateRange(1, [int]::MaxValue)]
  [int]$Steps = 20,
  [ValidateSet("robot0_agentview_left", "robot0_agentview_right", "robot0_eye_in_hand")]
  [string]$Camera = "robot0_agentview_left",
  [ValidateRange(64, 2048)]
  [int]$CameraWidth = 256,
  [ValidateRange(64, 2048)]
  [int]$CameraHeight = 256,
  [ValidateRange(256, 3840)]
  [int]$GuiWidth = 768,
  [switch]$NoGui,
  [switch]$Full
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $RoboCasaRoot) {
  $RoboCasaRoot = $env:ROBOCASA_ROOT
}
if (-not $RoboCasaRoot) {
  $RoboCasaRoot = Join-Path $repositoryRoot ".local\robocasa"
}
if (-not [IO.Path]::IsPathRooted($RoboCasaRoot)) {
  $RoboCasaRoot = Join-Path $repositoryRoot $RoboCasaRoot
}
$RoboCasaRoot = [IO.Path]::GetFullPath($RoboCasaRoot)
$venv = Join-Path $repositoryRoot ".local\robocasa-venv"
$venvPython = Join-Path $venv "Scripts\python.exe"
$sourceChecker = Join-Path $repositoryRoot "tools\robocasasource.py"
$sourceValid = $false
if (Test-Path $venvPython) {
  & python $sourceChecker check --path $RoboCasaRoot *> $null
  $sourceValid = $LASTEXITCODE -eq 0
}
$needsFullAssets = $Full -or $Task -ne "CloseFridge" -or $KitchenScene
if (-not $sourceValid -or -not (Test-Path (Join-Path $venv ".robocasa-installed")) -or
    -not (Test-Path (Join-Path $RoboCasaRoot ".assets-ready")) -or
    ($needsFullAssets -and -not (Test-Path (Join-Path $RoboCasaRoot ".assets-full-ready")))) {
  $confirmation = Read-Host "RoboCasa setup is incomplete. Download source, Python runtime, and assets now? [y/N]"
  if ($confirmation -notin @("y", "Y")) {
    throw "RoboCasa setup cancelled."
  }
  $setupArguments = @("-RoboCasaRoot", $RoboCasaRoot)
  if ($needsFullAssets) { $setupArguments += "-Full" }
  & (Join-Path $PSScriptRoot "robocasasetup.ps1") @setupArguments
}

$runArguments = @(
  (Join-Path $repositoryRoot "tools\robocasahrun.py"),
  "--task", $Task, "--split", $Split,
  "--seed", "$Seed", "--steps", "$Steps",
  "--camera", $Camera, "--camera-width", "$CameraWidth",
  "--camera-height", "$CameraHeight", "--gui-width", "$GuiWidth"
)
if ($KitchenScene) { $runArguments += @("--kitchen-scene", $KitchenScene) }
if ($NoGui) { $runArguments += "--no-gui" } else { $runArguments += "--gui" }

& $venvPython @runArguments
if ($LASTEXITCODE -ne 0) { throw "RoboCasa run failed (exit code $LASTEXITCODE)." }
