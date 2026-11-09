# SCHOENI DIGITAL CLI (`sdc`) — Installations-Skript für Windows
#
# Schnelle 1-Zeiler-Installation in PowerShell:
#   irm https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.ps1 | iex
# oder lokal im Repo:
#   .\install.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╭────────────────────────────────────────────────────────╮" -ForegroundColor Cyan
Write-Host "│  ◆ SCHOENI DIGITAL · sdc Installations-Assistent       │" -ForegroundColor Cyan
Write-Host "│  Plattform: Microsoft Windows (PowerShell)             │" -ForegroundColor Gray
Write-Host "╰────────────────────────────────────────────────────────╯" -ForegroundColor Cyan
Write-Host ""

# 1. uv prüfen oder installieren
Write-Host "ℹ Prüfe Python-Paketmanager uv …" -ForegroundColor Cyan
$uv = Get-Command uv -ErrorAction SilentlyContinue

if (-not $uv) {
    $uvLocal = Join-Path $HOME ".local\bin\uv.exe"
    $uvCargo = Join-Path $HOME ".cargo\bin\uv.exe"
    if (Test-Path $uvLocal) {
        $uv = $uvLocal
    } elseif (Test-Path $uvCargo) {
        $uv = $uvCargo
    } else {
        Write-Host "ℹ Installiere uv von https://astral.sh/uv …" -ForegroundColor Cyan
        try {
            irm https://astral.sh/uv/install.ps1 | iex
            $uv = Join-Path $HOME ".local\bin\uv.exe"
        } catch {
            Write-Error "✖ uv liess sich nicht installieren: $_"
            exit 1
        }
    }
}

Write-Host "✔ uv ist bereit: & $uv --version" -ForegroundColor Green

# 2. PATH aktualisieren
$localBin = Join-Path $HOME ".local\bin"
if ($env:Path -notlike "*$localBin*") {
    $env:Path = "$localBin;" + $env:Path
    [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)
}

# 3. sdc installieren
Write-Host "ℹ Installiere 'sdc' via uv tool …" -ForegroundColor Cyan
$scriptDir = $PSScriptRoot

if ($scriptDir -and (Test-Path (Join-Path $scriptDir "pyproject.toml"))) {
    & $uv tool install --force --editable $scriptDir
} else {
    $repoUrl = "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/cli.git"
    try {
        & $uv tool install --force "git+$repoUrl"
    } catch {
        Write-Host "▲ SSH fehlgeschlagen, versuche HTTPS …" -ForegroundColor Yellow
        & $uv tool install --force "git+https://git.schoeni-digital.com/schoeni-digital/cli.git"
    }
}

$sdc = Get-Command sdc -ErrorAction SilentlyContinue
if (-not $sdc) {
    $sdcPath = Join-Path $localBin "sdc.exe"
    if (Test-Path $sdcPath) {
        $sdc = $sdcPath
    }
}

if (-not $sdc) {
    Write-Warning "▲ 'sdc' liegt in $localBin, bitte neues PowerShell-Fenster öffnen falls der Befehl noch nicht erkannt wird."
} else {
    Write-Host "✔ sdc erfolgreich installiert!" -ForegroundColor Green
    Write-Host ""
    try {
        & $sdc doctor
    } catch {
        # ignore doctor errors during first setup
    }
}

Write-Host ""
Write-Host "╭────────────────────────────────────────────────────────╮" -ForegroundColor Green
Write-Host "│  ✔ Bereit! Starte sdc jetzt mit:                       │" -ForegroundColor Green
Write-Host "│     sdc                                                │" -ForegroundColor Cyan
Write-Host "│  Oder Notebook registrieren mit:                       │" -ForegroundColor Gray
Write-Host "│     sdc device add                                     │" -ForegroundColor Cyan
Write-Host "╰────────────────────────────────────────────────────────╯" -ForegroundColor Green
Write-Host ""
