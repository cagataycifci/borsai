[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Checking prerequisites..." -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 3.11+ is required." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 20+ is required." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm is required." }

$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$nodeMajor = [int]((node -p "process.versions.node.split('.')[0]").Trim())
if ([version]$pythonVersion -lt [version]"3.11") { throw "Python 3.11+ is required; found $pythonVersion." }
if ($nodeMajor -lt 20) { throw "Node.js 20+ is required; found $(node --version)." }

Write-Host "Installing Node dependencies from package-lock.json..." -ForegroundColor Yellow
npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }

$Engine = Join-Path $Root "services\engine"
$Venv = Join-Path $Engine ".venv"
if (-not (Test-Path $Venv)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv $Venv
}

$Python = Join-Path $Venv "Scripts\python.exe"
Write-Host "Installing engine and development dependencies..." -ForegroundColor Yellow
& $Python -m pip install --upgrade pip
& $Python -m pip install -e "$Engine[dev]"

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
}

Write-Host "Running verification..." -ForegroundColor Yellow
Push-Location $Engine
& $Python -m ruff check app
& $Python -m pytest -q
Pop-Location
npm run typecheck -w apps/desktop
npm run build -w apps/desktop

Write-Host "Setup and verification completed." -ForegroundColor Green
Write-Host "Start development with: npm run dev"
