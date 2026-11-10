[CmdletBinding()]
param(
  [switch]$Full,
  [string]$RoboCasaRoot
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
$suite = Join-Path $repositoryRoot ".local\robosuite"
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
  throw "Python is required to set up RoboCasa. Install Python 3.11 and ensure python.exe is on PATH."
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git is required to download RoboCasa. Install Git for Windows and ensure git.exe is on PATH."
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "uv is required to create the private Python 3.11 environment. Install it and ensure uv.exe is on PATH."
}

& python (Join-Path $repositoryRoot "tools\robocasasource.py") download --path $RoboCasaRoot
if ($LASTEXITCODE -ne 0) { throw "RoboCasa source setup failed (exit code $LASTEXITCODE)." }

$venvPython = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  & uv venv --python 3.11 --managed-python $venv
  if ($LASTEXITCODE -ne 0) { throw "Creating the RoboCasa Python environment failed (exit code $LASTEXITCODE)." }
}

$suiteSetup = Join-Path $suite "setup.py"
if (-not (Test-Path $suiteSetup)) {
  if (Test-Path $suite) {
    throw "The robosuite target exists but is not a checkout: $suite"
  }
  & git clone --filter=blob:none --depth 1 https://github.com/ARISE-Initiative/robosuite.git $suite
  if ($LASTEXITCODE -ne 0) { throw "Cloning robosuite failed (exit code $LASTEXITCODE)." }
}
$suiteRevision = "5ce6643f3092639d08f7b0f90ed1c6a84f50552c"
$currentRevision = (& git -C $suite rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not read the robosuite revision." }
if ($currentRevision -ne $suiteRevision) {
  & git -C $suite fetch --depth 1 origin $suiteRevision
  if ($LASTEXITCODE -ne 0) { throw "Fetching the pinned robosuite revision failed (exit code $LASTEXITCODE)." }
  & git -C $suite checkout --detach $suiteRevision
  if ($LASTEXITCODE -ne 0) { throw "Checking out the pinned robosuite revision failed (exit code $LASTEXITCODE)." }
}

$installMarker = Join-Path $venv ".robocasa-installed"
if (-not (Test-Path $installMarker)) {
  & uv pip install --python $venvPython -e $suite -e $RoboCasaRoot
  if ($LASTEXITCODE -ne 0) { throw "Installing RoboCasa and robosuite failed (exit code $LASTEXITCODE)." }
  New-Item -ItemType File -Path $installMarker -Force | Out-Null
}
if (-not (Test-Path (Join-Path $RoboCasaRoot "robocasa\macros_private.py"))) {
  & $venvPython -m robocasa.scripts.setup_macros
  if ($LASTEXITCODE -ne 0) { throw "Initializing RoboCasa macros failed (exit code $LASTEXITCODE)." }
}
if (-not (Test-Path (Join-Path $suite "robosuite\macros_private.py"))) {
  & $venvPython -m robosuite.scripts.setup_macros
  if ($LASTEXITCODE -ne 0) { throw "Initializing robosuite macros failed (exit code $LASTEXITCODE)." }
}

$assetsReady = Join-Path $RoboCasaRoot ".assets-ready"
$fullAssetsReady = Join-Path $RoboCasaRoot ".assets-full-ready"
if (-not (Test-Path $assetsReady) -or ($Full -and -not (Test-Path $fullAssetsReady))) {
  $env:HF_HOME = Join-Path $repositoryRoot ".local\huggingface"
  New-Item -ItemType Directory -Path $env:HF_HOME -Force | Out-Null
  $assetArguments = @((Join-Path $repositoryRoot "tools\robocasaassets.py"), $RoboCasaRoot)
  if ($Full) { $assetArguments += "--full" }
  & $venvPython @assetArguments
  if ($LASTEXITCODE -ne 0) { throw "Downloading RoboCasa assets failed (exit code $LASTEXITCODE)." }
}

Write-Host "RoboCasa is ready at $RoboCasaRoot"
